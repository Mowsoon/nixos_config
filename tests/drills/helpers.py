import base64
import datetime as dt
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
SYSTEM_PROFILE = "/nix/var/nix/profiles/system"
LOADER_GUID = "4a67b082-0a4c-41cf-b6c7-440b29bb8c4f"
POWER_CUT_TIMEOUT = dt.timedelta(minutes=5)
PCRLOCK_POLICY = "/var/lib/systemd/pcrlock.json"
RECOVERY_KEY = re.compile(r"[cbdefghijklnrtuv]{8}(?:-[cbdefghijklnrtuv]{8}){7}")


def unlock_with_passphrase(timeout: dt.timedelta | None = None) -> None:
    machine.wait_for_console_text(LUKS_PROMPT, timeout)
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


def create_pcrlock_policy() -> str:
    machine.wait_for_unit("systemd-pcrlock-firmware-code.service")
    output = machine.succeed("pcrlock-make-policy --recovery-pin=show 2>&1")
    print(output)
    match = RECOVERY_KEY.search(output)
    assert match is not None, f"No recovery PIN in: {output}"
    return match.group(0)


def enroll_tpm2_pcrlock() -> None:
    machine.succeed(
        f"PASSWORD={TEST_PASSPHRASE} systemd-cryptenroll {LUKS_DEVICE}"
        f" --tpm2-device=auto --tpm2-pcrlock={PCRLOCK_POLICY} --tpm2-pcrs=7"
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


def pcr(index: int) -> str:
    return machine.succeed(f"cat /sys/class/tpm/tpm0/pcr-sha256/{index}").strip()


def pcr7() -> str:
    return pcr(7)


def power_cut_when(condition: str) -> None:
    machine.succeed(
        "systemd-run --unit=drill-power-cut"
        f" sh -c 'until {condition}; do :; done; echo b > /proc/sysrq-trigger'"
    )


def boot_after_power_cut() -> None:
    unlock_with_passphrase(POWER_CUT_TIMEOUT)
    machine.wait_for_unit("multi-user.target")
    print(machine.succeed("journalctl -b -o cat --unit 'systemd-fsck@*'"))
    print(machine.succeed(f"ls -l {SYSTEM_PROFILE}*"))


def profile_generation() -> int:
    match = re.search(r"system-(\d+)-link", machine.succeed(f"readlink {SYSTEM_PROFILE}"))
    assert match is not None
    return int(match.group(1))


def rebuild_command(system: str, action: str) -> str:
    return (
        f"/run/current-system/sw/bin/nix-env --profile {SYSTEM_PROFILE} --set {system}"
        f" && {system}/bin/switch-to-configuration {action}"
    )


def booted_entry() -> str:
    raw = base64.b64decode(
        machine.succeed(
            f"base64 -w0 /sys/firmware/efi/efivars/LoaderEntrySelected-{LOADER_GUID}"
        )
    )
    return raw[4:].decode("utf-16-le").rstrip("\x00")


def assert_esp_consistent() -> None:
    machine.fail("ls /boot/EFI/Linux/*.tmp /boot/EFI/nixos/*.tmp")
    report = machine.succeed("sbctl verify 2>&1")
    print(report)
    unsigned = [
        line
        for line in report.splitlines()
        if "\u2717" in line and "/EFI/nixos/" not in line
    ]
    t.assertEqual([], unsigned)
