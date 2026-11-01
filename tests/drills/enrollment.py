import json

with subtest("The recovery key and the TPM2 slot are enrolled"):
    provision()
    metadata = json.loads(
        machine.succeed(f"cryptsetup luksDump --dump-json-metadata {LUKS_DEVICE}")
    )
    tokens = {token["type"]: token for token in metadata["tokens"].values()}
    t.assertIn("systemd-recovery", tokens)
    t.assertEqual([7], tokens["systemd-tpm2"]["tpm2-pcrs"])

with subtest("The TPM2 unlocks the container without a passphrase"):
    machine.shutdown()
    boot_with_tpm2()
    assert_secure_boot_enabled()
