with subtest("The machine is provisioned and the TPM is cleared"):
    recovery_key = provision()
    machine.succeed("tpm2_clear")
    machine.shutdown()

with subtest("The unseal fails and the recovery key opens the container"):
    machine.start(allow_reboot=True)
    machine.wait_for_console_text(LUKS_PROMPT)
    machine.send_console(f"{recovery_key}\n")
    machine.wait_for_unit("multi-user.target")
    assert_secure_boot_enabled()

with subtest("A new TPM2 enrollment restores the automatic unlock"):
    machine.succeed("systemd-analyze pcrs 7")
    machine.succeed(f"systemd-cryptenroll {LUKS_DEVICE} --wipe-slot=tpm2")
    machine.succeed(
        f"PASSWORD={recovery_key} systemd-cryptenroll {LUKS_DEVICE}"
        " --tpm2-device=auto --tpm2-pcrs=7"
    )
    assert_one_tpm2_token_on_pcr7()
    machine.shutdown()
    boot_with_tpm2()
    assert_secure_boot_enabled()
