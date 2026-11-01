with subtest("The first boot generates the keys and the firmware enrolls them"):
    machine.start(allow_reboot=True)
    unlock_with_passphrase()
    unlock_with_passphrase()
    machine.wait_for_unit("multi-user.target")
    assert_secure_boot_enabled()

with subtest("A power loss rolls the root back and keeps the persisted state"):
    machine.succeed("touch /root-marker /persist/persist-marker", "sync")
    machine.crash()
    boot_with_passphrase()
    machine.fail("test -e /root-marker")
    machine.succeed("test -e /persist/persist-marker")
    assert_secure_boot_enabled()
    t.assertEqual(
        "ConditionResult=no",
        machine.succeed(
            "systemctl show --property=ConditionResult generate-sb-keys.service"
        ).strip(),
    )
