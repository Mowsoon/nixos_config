with subtest("The machine is provisioned and the TPM is cleared"):
    recovery_key, _ = provision()
    machine.succeed("tpm2_clear")
    machine.shutdown()

with subtest("The unseal fails and the recovery key opens the container"):
    recover_with_key(recovery_key)

with subtest("A new pcrlock policy and TPM2 enrollment restore the automatic unlock"):
    recreate_pcrlock_policy()
    reenroll_tpm2(recovery_key)
    machine.shutdown()
    boot_with_tpm2()
    assert_secure_boot_enabled()
    machine.wait_for_unit(MAKE_POLICY_UNIT)
