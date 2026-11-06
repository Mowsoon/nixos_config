# Firmware update

## Overview

A firmware update changes PCR 0, which the TPM2 slot of the root container checks through the
systemd-pcrlock policy described in
[Firmware code lock](../architecture/boot-chain.md#firmware-code-lock). Prepared beforehand, the
update keeps the unattended boot: `pcr0-predict` computes the PCR 0 records of the new firmware
from the vendor capsule and writes them as a second variant of the firmware code, and the policy
accepts the running and the next firmware during the update boot. Unprepared, the first boot of
the new firmware asks for the recovery key, and the new firmware is accepted only with the
recovery PIN.

Each policy rewrite of the procedure also changes the policy copy on the ESP, measured in PCR 12.
`pcrlock-make-policy` renews the TPM2 slot for it before returning, as described in
[Credentials lock](../architecture/boot-chain.md#credentials-lock); its output ends with
`sealed the TPM2 slot to PCR 7 and PCR 12`. No step of the procedure touches the slot by hand.

`pcr0-predict` needs the capsule of the running version as well as the new one. With the running
capsule it recomputes the current PCR 0 and compares it with the event log and with
`generated.pcrlock`; a mismatch means the file is not the running firmware, or the firmware
measures differently than the tool expects, and nothing is predicted. Keep the capsule of each
installed version until the next update.

The update is flashed from the firmware setup with ASUS EZ Flash, never from Linux: AMD ROM Armor
(`rom_armor_enforced` is `1`) leaves writes to the flash to the firmware. Windows can flash a new
firmware on its own, without a prediction, through two paths. Windows Update installs vendor
firmware as a driver of the system firmware device, which the firmware publishes in its EFI System
Resource Table (ESRT) under the hardware ID `UEFI\RES_{<firmware-class>}`; Windows hands the
capsule to the firmware, which flashes it at the next restart. MyASUS and Armoury Crate offer BIOS
updates through their own updater, which stages the same capsule. Windows is therefore told never
to install a driver for that device, and the ASUS applications never to update the BIOS. A
firmware flashed anyway is caught at the next NixOS boot, which takes the recovery path below.

## How to update the firmware

Blast radius: the firmware of the machine and the pcrlock policy. A wrong prediction costs one
recovery key at boot and the recovery PIN; a failed flash is handled by the vendor tool. Rollback
path: none for the firmware, whose capsule update refuses older versions (the lowest supported
version of its ESRT entry is the running one); the previous firmware stays allowed by the policy
until the new one boots, so a cancelled flash boots unattended.

Prerequisites: the capsule of the running version and the new capsule, both downloaded from the
ASUS support page of the model and extracted; the LUKS recovery key and the recovery PIN at hand;
a FAT32 USB stick.

1. Check that the running capsule reproduces PCR 0.

   ```bash
   sudo pcr0-predict check <current-capsule>
   ```

   `<current-capsule>` is the file of the version shown by `cat /sys/class/dmi/id/bios_version`.
   The last line reads `<current-capsule> reproduces PCR 0 of the running firmware`.

2. Predict the new firmware and write the variant.

   ```bash
   sudo pcr0-predict predict <current-capsule> <new-capsule>
   ```

   `<new-capsule>` is the file of the new version. The command prints the predicted records and
   writes `/var/lib/pcrlock.d/250-firmware-code-early.pcrlock.d/predicted.pcrlock`. A refusal names
   the check that failed; then either keep the running firmware, or flash and follow
   [How to recover from an unpredicted update](#how-to-recover-from-an-unpredicted-update).

3. Rewrite the policy with both variants. The output reports that the NV index was updated and
   that the TPM2 slot was sealed again.

   ```bash
   sudo pcrlock-make-policy
   ```

4. Copy the new capsule to the root of the USB stick, then restart into the firmware setup.

   ```bash
   systemctl reboot --firmware-setup
   ```

5. Flash the new capsule from EZ Flash. If the firmware asks whether to reset the fTPM, answer
   no: a reset clears the TPM and requires
   [recreating the pcrlock policy](luks-enrollment.md#how-to-recreate-the-pcrlock-policy-after-a-tpm-clear).
6. Boot NixOS. The container opens without a prompt. Check the version.

   ```bash
   cat /sys/class/dmi/id/bios_version
   ```

7. Remove the variant and rewrite the policy, so that it allows the new firmware alone.

   ```bash
   sudo rm /var/lib/pcrlock.d/250-firmware-code-early.pcrlock.d/predicted.pcrlock
   sudo pcrlock-make-policy
   ```

8. Check that the new capsule now reproduces PCR 0, and keep it for the next update.

   ```bash
   sudo pcr0-predict check <new-capsule>
   ```

## How to keep Windows from flashing the firmware

Blast radius: Windows no longer installs any driver for the system firmware device, so it never
offers a firmware update again; other drivers are not affected. Rollback path: delete the policy
key of step 3 and restart Windows.

1. On NixOS, read the firmware class of the system firmware entry of the ESRT. The entry whose
   `fw_type` is `1` is the system firmware.

   ```bash
   sudo grep . /sys/firmware/efi/esrt/entries/*/fw_class /sys/firmware/efi/esrt/entries/*/fw_type
   ```

2. In Windows, open Device Manager, then Firmware, then the properties of System Firmware. On the
   Details tab, the Hardware Ids property shows `UEFI\RES_{<firmware-class>}`, with the GUID of
   step 1.
3. In a terminal run as administrator, deny the installation of drivers for that hardware ID.
   The keys are those of the Group Policy "Prevent installation of devices that match any of these
   device IDs", which Windows Home lacks as a console but honours in the registry.

   ```bat
   reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions" /v DenyDeviceIDs /t REG_DWORD /d 1 /f
   reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions" /v DenyDeviceIDsRetroactive /t REG_DWORD /d 0 /f
   reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions\DenyDeviceIDs" /v 1 /t REG_SZ /d "UEFI\RES_{<firmware-class>}" /f
   ```

   `<firmware-class>` is the GUID of step 1, without braces. `DenyDeviceIDsRetroactive` set to
   `0` leaves the driver already installed in place, so the device keeps working; only a new
   version is refused.

4. Restart Windows, then check that the policy is read.

   ```bat
   reg query "HKLM\SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions" /s
   ```

   A firmware update offered later by Windows Update then fails to install, which is the
   expected result.

5. In MyASUS and in Armoury Crate, turn off the automatic updates of the BIOS and never start a
   BIOS update from them. The labels of these settings change between versions of the
   applications, so check them after each update of MyASUS or Armoury Crate.

## How to recover from an unpredicted update

1. At the passphrase prompt of the first boot, type the recovery key.
2. Check that the firmware version is the one installed on purpose.

   ```bash
   cat /sys/class/dmi/id/bios_version
   ```

3. Accept the running firmware as in
   [LUKS enrollment](luks-enrollment.md#how-to-accept-the-running-firmware), then remove any
   `predicted.pcrlock` left from step 2 of the update.

## Reference

### Checks of pcr0-predict

| Check | Refusal means |
| --- | --- |
| The file is an EFI capsule whose header and image sizes match the file | Not a capsule, or a truncated download |
| `generated.pcrlock` holds the PCR 0 records of the event log | The firmware code lock of this boot is missing or stale |
| PCR 0 holds an S-CRTM version and one firmware volume, then the separator | The firmware measures more than the tool models |
| The running capsule holds the measured volume at its logged address, with its digest | The file is not the running firmware |
| The modules that store the S-CRTM data in the running capsule store it in the new one | The S-CRTM version may change; it cannot be predicted |
| The new capsule holds exactly one volume with the name of the measured volume | The volume layout changed |

### Paths

| Path | Content |
| --- | --- |
| `/sys/kernel/security/tpm0/binary_bios_measurements` | Event log of the running firmware, read by `pcr0-predict` |
| `/var/lib/pcrlock.d/250-firmware-code-early.pcrlock.d/generated.pcrlock` | PCR 0 records of the running firmware, written at every boot |
| `/var/lib/pcrlock.d/250-firmware-code-early.pcrlock.d/predicted.pcrlock` | PCR 0 records of the next firmware, written by `pcr0-predict` |
