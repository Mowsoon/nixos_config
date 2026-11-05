INJECTED = "/boot/loader/credentials/tmpfiles.extra.cred"

with subtest("The TPM2 slot is sealed to PCR 7 and to the ESP credentials in PCR 12"):
    recovery_key, _ = provision()
    assert_one_tpm2_token()
    machine.shutdown()
    boot_with_tpm2()
    machine.wait_for_unit(MAKE_POLICY_UNIT)
    pcr12_sealed = pcr(12)

with subtest("A credential dropped on the ESP fails the unseal and is never sealed"):
    machine.succeed(f"echo injected > {INJECTED}", "sync")
    machine.shutdown()
    recover_with_key(recovery_key)
    t.assertNotEqual(pcr12_sealed, pcr(12))
    assert_reseal_refused()
    assert_one_tpm2_token()

with subtest("Once the credential is removed, the unattended boot comes back"):
    machine.succeed(f"rm {INJECTED}", "sync")
    machine.shutdown()
    boot_with_tpm2()
    t.assertEqual(pcr12_sealed, pcr(12))
    machine.wait_for_unit(MAKE_POLICY_UNIT)
