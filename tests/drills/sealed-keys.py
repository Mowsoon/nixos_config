PKI = "/var/lib/sbctl/keys"
UNSEALED = "/run/secure-boot-keys"

with subtest("The Secure Boot private keys are sealed to PCR 15 and removed in plain text"):
    recovery_key, recovery_pin = provision()
    machine.shutdown()
    boot_with_tpm2()
    print(machine.succeed("secure-boot-keys seal"))
    machine.succeed(f"rm {PKI}/PK/PK.key {PKI}/KEK/KEK.key {PKI}/db/db.key")
    machine.succeed(f"test -e {PKI}/db/db.key.cred -a -e {PKI}/KEK/KEK.key.cred -a -e {PKI}/PK/PK.key.cred")

with subtest("The boot loader hook signs a new generation with the unsealed key and wipes it"):
    machine.succeed(rebuild_command(next_system, "boot"))
    machine.fail(f"test -e {UNSEALED}")
    assert_esp_consistent()
    machine.shutdown()
    boot_with_tpm2()
    assert_secure_boot_enabled()
    t.assertIn("nixos-generation-2-", booted_entry())

with subtest("sbctl signs the firmware databases with the unsealed keys"):
    print(machine.succeed("secure-boot-keys sbctl verify"))
    exported = machine.succeed(
        "cd $(mktemp -d) && secure-boot-keys sbctl enroll-keys --microsoft --export auth >&2"
        " && ls *.auth"
    )
    t.assertEqual(["KEK.auth", "PK.auth", "db.auth"], sorted(exported.split()))
    machine.fail(f"test -e {UNSEALED}")

with subtest("The keys no longer decrypt once PCR 15 holds another value"):
    machine.succeed("/run/current-system/sw/lib/systemd/systemd-pcrextend --pcr=15 drill")
    status, output = machine.execute("secure-boot-keys unseal 2>&1")
    print(output)
    t.assertNotEqual(0, status)
    machine.succeed("secure-boot-keys wipe")
