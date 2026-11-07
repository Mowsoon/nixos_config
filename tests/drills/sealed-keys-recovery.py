PKI = "/var/lib/sbctl/keys"
UNSEALED = "/run/secure-boot-keys"
RECOVERY_COPY = "/persist/sbctl-keys.tar"
PLAIN_KEYS = f"{PKI}/PK/PK.key {PKI}/KEK/KEK.key {PKI}/db/db.key"

with subtest("The keys are sealed after their recovery copy, then the TPM is cleared"):
    recovery_key, _ = provision()
    machine.succeed(f"tar --create --file={RECOVERY_COPY} -C / var/lib/sbctl/keys")
    machine.succeed("secure-boot-keys seal")
    machine.succeed(f"rm {PLAIN_KEYS}")
    machine.succeed("tpm2_clear")
    machine.shutdown()

with subtest("The recovery key opens the container, but the keys no longer decrypt"):
    recover_with_key(recovery_key)
    t.assertNotEqual("0" * 64, pcr(15))
    status, output = machine.execute("secure-boot-keys unseal 2>&1")
    print(output)
    t.assertNotEqual(0, status)
    t.assertIn("restore the plain keys from the recovery copy", output)
    machine.fail(f"test -e {UNSEALED}")

with subtest("A rebuild fails before lanzaboote writes anything to the ESP"):
    status, output = machine.execute(rebuild_command(next_system, "boot") + " 2>&1")
    print(output)
    t.assertNotEqual(0, status)
    machine.fail(f"test -e {UNSEALED}")
    machine.fail("ls /boot/EFI/Linux/nixos-generation-2-*")
    t.assertEqual(2, profile_generation())

with subtest("The recovery copy restores the keys, sealed again to the new TPM"):
    recreate_pcrlock_policy()
    reenroll_tpm2(recovery_key)
    machine.succeed(f"tar --extract --file={RECOVERY_COPY} -C /")
    print(machine.succeed("secure-boot-keys seal"))
    machine.succeed(f"rm {PLAIN_KEYS}")
    machine.succeed(f"{next_system}/bin/switch-to-configuration boot")
    assert_esp_consistent()
    machine.shutdown()
    boot_with_tpm2()
    assert_secure_boot_enabled()
    t.assertIn("nixos-generation-2-", booted_entry())
