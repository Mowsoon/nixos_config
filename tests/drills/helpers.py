import json
import os
import re
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

LUKS_DEVICE = "/dev/disk/by-partlabel/disk-main-luks"
LUKS_PROMPT = "Please enter passphrase (or recovery key )?for disk"
TEST_PASSPHRASE = "disko"
BOOT_DONE = "Reached target Multi-User System"
RECOVERY_KEY = re.compile(r"[cbdefghijklnrtuv]{8}(?:-[cbdefghijklnrtuv]{8}){7}")


def unlock_with_passphrase() -> None:
    machine.wait_for_console_text(LUKS_PROMPT)
    machine.send_console(f"{TEST_PASSPHRASE}\n")
    machine.connected = False
    machine.connect()


def boot_with_passphrase() -> None:
    machine.start(allow_reboot=True)
    unlock_with_passphrase()
    machine.wait_for_unit("multi-user.target")


def boot_with_tpm2() -> None:
    machine.start(allow_reboot=True)
    machine.wait_for_console_text(f"{LUKS_PROMPT}|{BOOT_DONE}")
    t.assertNotRegex(machine.get_console_log(), LUKS_PROMPT)
    machine.connect()


def assert_secure_boot_enabled() -> None:
    t.assertIn("Secure Boot: enabled (user)", machine.succeed("bootctl status"))


def first_boot() -> None:
    machine.start(allow_reboot=True)
    unlock_with_passphrase()
    unlock_with_passphrase()
    machine.wait_for_unit("multi-user.target")
    assert_secure_boot_enabled()


def enroll_recovery_key() -> str:
    output = machine.succeed(
        f"PASSWORD={TEST_PASSPHRASE} systemd-cryptenroll {LUKS_DEVICE} --recovery-key 2>&1"
    )
    match = RECOVERY_KEY.search(output)
    assert match is not None, f"No recovery key in: {output}"
    return match.group(0)


def enroll_tpm2() -> None:
    machine.succeed(
        f"PASSWORD={TEST_PASSPHRASE} systemd-cryptenroll {LUKS_DEVICE}"
        " --tpm2-device=auto --tpm2-pcrs=7"
    )


def luks_tokens() -> list[dict]:
    metadata = json.loads(
        machine.succeed(f"cryptsetup luksDump --dump-json-metadata {LUKS_DEVICE}")
    )
    return list(metadata["tokens"].values())


def assert_one_tpm2_token_on_pcr7() -> None:
    pcrs = [
        token["tpm2-pcrs"] for token in luks_tokens() if token["type"] == "systemd-tpm2"
    ]
    t.assertEqual([[7]], pcrs)


def provision() -> str:
    first_boot()
    recovery_key = enroll_recovery_key()
    enroll_tpm2()
    return recovery_key


def recover_with_key(recovery_key: str) -> None:
    machine.start(allow_reboot=True)
    machine.wait_for_console_text(LUKS_PROMPT)
    machine.send_console(f"{recovery_key}\n")
    machine.wait_for_unit("multi-user.target")
    assert_secure_boot_enabled()


def reenroll_tpm2(recovery_key: str) -> None:
    machine.succeed("systemd-analyze pcrs 7")
    machine.succeed(f"systemd-cryptenroll {LUKS_DEVICE} --wipe-slot=tpm2")
    machine.succeed(
        f"PASSWORD={recovery_key} systemd-cryptenroll {LUKS_DEVICE}"
        " --tpm2-device=auto --tpm2-pcrs=7"
    )
    assert_one_tpm2_token_on_pcr7()


def pcr7() -> str:
    return machine.succeed("cat /sys/class/tpm/tpm0/pcr-sha256/7").strip()
