SBCTL_KEYS = "/var/lib/sbctl/keys"
DBX_VARIABLE = "/sys/firmware/efi/efivars/dbx-d719b2cb-3d3a-4596-a3bc-dad00e67656f"

with subtest("The machine is provisioned and a signed entry is appended to dbx"):
    recovery_key, _ = provision()
    pcr7_before = pcr7()
    machine.succeed(
        "openssl req -new -x509 -newkey rsa:2048 -nodes -days 1"
        " -subj '/CN=Revoked drill certificate/'"
        " -keyout /tmp/revoked.key -out /tmp/revoked.pem",
        "cert-to-efi-sig-list -g $(cat /var/lib/sbctl/GUID) /tmp/revoked.pem /tmp/revoked.esl",
        f"sign-efi-sig-list -a -k {SBCTL_KEYS}/KEK/KEK.key -c {SBCTL_KEYS}/KEK/KEK.pem"
        " dbx /tmp/revoked.esl /tmp/revoked.auth",
        f"if [ -e {DBX_VARIABLE} ]; then chattr -i {DBX_VARIABLE}; fi",
        "efi-updatevar -a -f /tmp/revoked.auth dbx",
    )
    machine.shutdown()

with subtest("PCR 7 changes, the unseal fails and the recovery key opens the container"):
    recover_with_key(recovery_key)
    t.assertNotEqual(pcr7_before, pcr7())

with subtest("A new TPM2 enrollment restores the automatic unlock"):
    reenroll_tpm2(recovery_key)
    machine.shutdown()
    boot_with_tpm2()
    assert_secure_boot_enabled()
