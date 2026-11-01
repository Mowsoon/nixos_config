with subtest("The recovery key and the TPM2 slot are enrolled"):
    provision()
    t.assertIn("systemd-recovery", [token["type"] for token in luks_tokens()])
    assert_one_tpm2_token_on_pcr7()

with subtest("The TPM2 unlocks the container without a passphrase"):
    machine.shutdown()
    boot_with_tpm2()
    assert_secure_boot_enabled()
