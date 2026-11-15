INJECTED = "/boot/loader/credentials/tmpfiles.extra.cred"
FIRMWARE_CODE_EARLY = "/var/lib/pcrlock.d/250-firmware-code-early.pcrlock.d"
FIRMWARE_VARIANT = f"{FIRMWARE_CODE_EARLY}/variant.pcrlock"


def tpm2_slots() -> list[dict]:
    return [token for token in luks_tokens() if token["type"] == "systemd-tpm2"]


def lockout_counter() -> str:
    output = machine.succeed("tpm2_getcap properties-variable")
    match = re.search(r"TPM2_PT_LOCKOUT_COUNTER:\s*(\S+)", output)
    assert match is not None, output
    return match.group(1)


def write_firmware_variant() -> None:
    lock = json.loads(machine.succeed(f"cat {FIRMWARE_CODE_EARLY}/generated.pcrlock"))
    record = next(record for record in lock["records"] if record["pcr"] == 0)
    for digest in record["digests"]:
        digest["digest"] = "0" * len(digest["digest"])
    machine.succeed(f"echo '{json.dumps(lock)}' > {FIRMWARE_VARIANT}")


def rewrite_policy(command: str) -> None:
    before = machine.succeed(f"cat {PCRLOCK_POLICY}")
    print(machine.succeed(f"{command} 2>&1"))
    t.assertNotEqual(before, machine.succeed(f"cat {PCRLOCK_POLICY}"))


with subtest("The machine is provisioned and boots unattended on one TPM2 slot"):
    provision()
    machine.shutdown()
    boot_with_tpm2()
    machine.wait_for_unit(MAKE_POLICY_UNIT)
    assert_one_tpm2_token()
    counter = lockout_counter()

with subtest("Three policy rewrites in one boot each reseal the TPM2 slot without a key"):
    rewrite_policy(rebuild_command(next_system, "boot"))
    write_firmware_variant()
    rewrite_policy(f"systemctl restart {MAKE_POLICY_UNIT}")
    machine.succeed(f"rm {FIRMWARE_VARIANT}")
    rewrite_policy(f"systemctl restart {MAKE_POLICY_UNIT}")
    machine.fail(f"test -e {PCR12_ALERT}")
    t.assertEqual(2, len(tpm2_slots()))

with subtest("The next boot unseals and removes the slot of the previous boot"):
    machine.shutdown()
    boot_with_tpm2()
    t.assertIn("nixos-generation-2-", booted_entry())
    machine.wait_for_unit(MAKE_POLICY_UNIT)
    print(machine.succeed("journalctl -b -o cat --unit systemd-cryptsetup@cryptroot.service"))
    print(machine.succeed(f"journalctl -b -o cat --unit {MAKE_POLICY_UNIT}"))
    assert_one_tpm2_token()
    t.assertEqual(counter, lockout_counter())

with subtest("A reseal refused during a rebuild raises the alert"):
    machine.succeed(f"echo injected > {INJECTED}", "sync")
    machine.fail(rebuild_command(next_system, "boot"))
    t.assertIn("pcrlock-make-policy", machine.succeed(f"cat {PCR12_ALERT}"))
