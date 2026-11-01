import os
import subprocess

disk_dir = str(machine.state_dir)
subprocess.run(
    [
        qemu_img,
        "create",
        "-f",
        "qcow2",
        "-b",
        disko_image,
        "-F",
        "qcow2",
        f"{disk_dir}/main.qcow2",
    ],
    check=True,
)
os.environ["tmp"] = disk_dir

LUKS_PROMPT = "Please enter passphrase for disk"
TEST_PASSPHRASE = "disko"


def unlock_with_passphrase() -> None:
    machine.wait_for_console_text(LUKS_PROMPT)
    machine.send_console(f"{TEST_PASSPHRASE}\n")
    machine.connected = False
    machine.connect()


def boot_with_passphrase() -> None:
    machine.start(allow_reboot=True)
    unlock_with_passphrase()
    machine.wait_for_unit("multi-user.target")


def assert_secure_boot_enabled() -> None:
    t.assertIn("Secure Boot: enabled (user)", machine.succeed("bootctl status"))
