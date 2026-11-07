ZERO = "0" * 64

with subtest("The unlock by the TPM2 slot measures the volume key into PCR 15"):
    recovery_key, recovery_pin = provision()
    machine.shutdown()
    boot_with_tpm2()
    print(machine.succeed("journalctl -b -o cat --unit 'systemd-cryptsetup@*'"))
    first = pcr(15)
    t.assertNotEqual(ZERO, first.lower())

with subtest("PCR 15 holds the same value at the next boot"):
    machine.shutdown()
    boot_with_tpm2()
    t.assertEqual(first, pcr(15))

with subtest("An unlock with the recovery key measures the same volume key"):
    machine.succeed(f"PASSWORD={TEST_PASSPHRASE} systemd-cryptenroll --wipe-slot=tpm2 {LUKS_DEVICE}")
    machine.shutdown()
    recover_with_key(recovery_key)
    t.assertEqual(first, pcr(15))
