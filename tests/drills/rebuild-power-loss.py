with subtest("The first boot enrolls the keys"):
    first_boot()
    original_system = machine.succeed(f"readlink -f {SYSTEM_PROFILE}-1-link").strip()

with subtest("A power cut while the boot loader installs generation 2 boots generation 1"):
    power_cut_when('set -- /boot/EFI/Linux/nixos-generation-2-*; [ -e "$1" ]')
    machine.succeed(
        f"systemd-run --unit=drill-rebuild sh -c '{rebuild_command(next_system, 'boot')}'"
    )
    boot_after_power_cut()
    t.assertIn("nixos-generation-1-", booted_entry())

with subtest("Running the interrupted rebuild again boots the new system"):
    machine.succeed(rebuild_command(next_system, "boot"))
    assert_esp_consistent()
    machine.shutdown()
    boot_with_passphrase()
    t.assertIn(f"nixos-generation-{profile_generation()}-", booted_entry())
    t.assertEqual("next", machine.succeed("cat /etc/drill-generation"))

with subtest("A power cut during the activation boots the generation being switched to"):
    interrupted_generation = profile_generation() + 1
    power_cut_when("[ ! -e /etc/drill-generation ]")
    machine.succeed(
        f"systemd-run --unit=drill-rebuild sh -c '{rebuild_command(original_system, 'switch')}'"
    )
    boot_after_power_cut()
    t.assertIn(f"nixos-generation-{interrupted_generation}-", booted_entry())
    machine.fail("test -e /etc/drill-generation")

with subtest("Running the interrupted switch again leaves a consistent ESP"):
    machine.succeed(rebuild_command(original_system, "switch"))
    assert_esp_consistent()
    machine.shutdown()
    boot_with_passphrase()
    t.assertIn(f"nixos-generation-{profile_generation()}-", booted_entry())
    machine.fail("test -e /etc/drill-generation")
