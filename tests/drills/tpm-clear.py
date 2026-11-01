with subtest("The machine is provisioned and the TPM is cleared"):
    recovery_key = provision()
    machine.succeed("tpm2_clear")
    machine.shutdown()

with subtest("The unseal fails and the recovery key opens the container"):
    recover_with_key(recovery_key)

with subtest("A new TPM2 enrollment restores the automatic unlock"):
    reenroll_tpm2(recovery_key)
    machine.shutdown()
    boot_with_tpm2()
    assert_secure_boot_enabled()
