FIRMWARE_CODE_EARLY = "/var/lib/pcrlock.d/250-firmware-code-early.pcrlock.d"
OTHER_FIRMWARE_LOCK = "/persist/other-firmware.pcrlock"
MAKE_POLICY_UNIT = "systemd-pcrlock-make-policy.service"

first_firmware = machine.start_command
other_firmware = type(first_firmware)(other_firmware_vm)


def boot_on(firmware) -> None:
    machine.shutdown()
    machine.start_command = firmware


def wait_for_policy_update() -> None:
    machine.wait_for_unit("systemd-pcrlock-firmware-code.service")
    machine.wait_for_unit(MAKE_POLICY_UNIT)


def assert_policy_update_refused() -> None:
    machine.wait_for_unit("systemd-pcrlock-firmware-code.service")
    machine.wait_until_succeeds(f"systemctl is-failed {MAKE_POLICY_UNIT}")
    print(machine.succeed(f"journalctl -b -o cat --unit {MAKE_POLICY_UNIT}"))


with subtest("The TPM2 slot binds the pcrlock policy of PCR 0 and the literal PCR 7"):
    first_boot()
    recovery_key = enroll_recovery_key()
    machine.fail(f"systemctl is-active {MAKE_POLICY_UNIT}")
    recovery_pin = create_pcrlock_policy()
    enroll_tpm2_pcrlock()
    tpm2_tokens = [token for token in luks_tokens() if token["type"] == "systemd-tpm2"]
    print(json.dumps(tpm2_tokens, indent=2))
    t.assertEqual(1, len(tpm2_tokens))
    t.assertEqual([7], tpm2_tokens[0]["tpm2-pcrs"])
    t.assertTrue(tpm2_tokens[0]["tpm2_pcrlock"])
    print(machine.succeed("ls -l /boot/loader/credentials"))
    first_pcr0 = pcr(0)
    boot_on(first_firmware)
    boot_with_tpm2()
    wait_for_policy_update()

with subtest("Another firmware build fails the unseal and is not locked by itself"):
    boot_on(other_firmware)
    recover_with_key(recovery_key)
    other_pcr0 = pcr(0)
    t.assertNotEqual(first_pcr0, other_pcr0)
    assert_policy_update_refused()
    machine.succeed(f"cp {FIRMWARE_CODE_EARLY}/generated.pcrlock {OTHER_FIRMWARE_LOCK}")

with subtest("Back on the first firmware, the policy left in place unseals"):
    boot_on(first_firmware)
    boot_with_tpm2()
    t.assertEqual(first_pcr0, pcr(0))
    wait_for_policy_update()

with subtest("A variant of the new firmware keeps the unattended boot across the update"):
    machine.succeed(
        f"cp {OTHER_FIRMWARE_LOCK} {FIRMWARE_CODE_EARLY}/predicted.pcrlock",
        f"systemctl restart {MAKE_POLICY_UNIT}",
    )
    boot_on(other_firmware)
    boot_with_tpm2()
    t.assertEqual(other_pcr0, pcr(0))
    wait_for_policy_update()
    machine.succeed(
        f"rm {FIRMWARE_CODE_EARLY}/predicted.pcrlock",
        f"systemctl restart {MAKE_POLICY_UNIT}",
    )

with subtest("Once the new firmware is locked, the previous one no longer unseals"):
    boot_on(first_firmware)
    recover_with_key(recovery_key)
    t.assertEqual(first_pcr0, pcr(0))
    assert_policy_update_refused()

with subtest("The recovery PIN locks the running firmware and restores the unattended boot"):
    machine.succeed(f"PIN={recovery_pin} pcrlock-make-policy --recovery-pin=query")
    boot_on(first_firmware)
    boot_with_tpm2()
    wait_for_policy_update()
