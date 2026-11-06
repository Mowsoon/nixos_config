LOADER_CONF = "/boot/loader/loader.conf"


def boot_entry_of(generation: int) -> str:
    entries = json.loads(machine.succeed("bootctl list --json=short"))
    ids = [entry["id"] for entry in entries if f"nixos-generation-{generation}-" in entry["id"]]
    t.assertEqual(1, len(ids), f"entries: {[entry['id'] for entry in entries]}")
    return ids[0]


def assert_policy_update_refused() -> None:
    machine.wait_until_succeeds(f"systemctl is-failed {MAKE_POLICY_UNIT}")
    print(machine.succeed(f"journalctl -b -o cat --unit {MAKE_POLICY_UNIT}"))


with subtest("The policy covers PCR 5 and the PCR 11 of the installed generation"):
    first_boot()
    print(machine.succeed("systemd-pcrlock log --no-pager 2>/dev/null | grep -E '^ +(5|11) '"))
    recovery_key = enroll_recovery_key()
    recovery_pin = create_pcrlock_policy()
    enroll_tpm2()
    assert_one_tpm2_token()
    print(machine.succeed("find /var/lib/pcrlock.d -name '*.pcrlock' | sort"))
    machine.shutdown()
    boot_with_tpm2()
    t.assertIn("nixos-generation-1-", booted_entry())

with subtest("A new generation installed by the boot loader hook unseals at its first boot"):
    machine.succeed(rebuild_command(next_system, "boot"))
    variants = machine.succeed("ls /var/lib/pcrlock.d/650-lanzaboote-generations.pcrlock.d")
    t.assertIn("nixos-generation-2-", variants)
    machine.shutdown()
    boot_with_tpm2()
    t.assertIn("nixos-generation-2-", booted_entry())
    t.assertEqual("next", machine.succeed("cat /etc/drill-generation"))
    machine.wait_for_unit(MAKE_POLICY_UNIT)

with subtest("The previous generation chosen in the boot menu still unseals"):
    machine.succeed(f"bootctl set-oneshot {boot_entry_of(1)}")
    machine.shutdown()
    boot_with_tpm2()
    t.assertIn("nixos-generation-1-", booted_entry())
    machine.fail("test -e /etc/drill-generation")
    machine.wait_for_unit(MAKE_POLICY_UNIT)

with subtest("A loader.conf changed by hand fails the unseal and is not accepted by itself"):
    machine.succeed(f"cp {LOADER_CONF} /persist/loader.conf")
    machine.succeed(f"echo 'timeout 5' >> {LOADER_CONF}")
    machine.shutdown()
    recover_with_key(recovery_key)
    assert_policy_update_refused()

with subtest("The original loader.conf unseals again with the policy left in place"):
    machine.succeed(f"cp /persist/loader.conf {LOADER_CONF}")
    machine.shutdown()
    boot_with_tpm2()
    machine.wait_for_unit(MAKE_POLICY_UNIT)
