# Installation

## Overview

The switch from Arch Linux to NixOS happens once, on the Linux NVMe disk (Samsung 990 PRO). The
Windows NVMe disk (WD SN560) and its BitLocker volume are never written. The procedure is
rehearsed end to end in a virtual machine before it runs on the workstation.

Three flake outputs support the procedure:

| Output | Role |
| --- | --- |
| `nixosConfigurations.installer` | Live system written to a USB key, with flakes, zram, `disko`, `age`, `sbctl`, `mkpasswd`, `efibootmgr` and `git` |
| `nixosConfigurations.hephaestus` | Target system installed on the workstation |
| `nixosConfigurations.hephaestus-rehearsal` | Same system, with the target disk path pointing at the rehearsal VM disk |

The installer image is not signed by a key enrolled in the firmware, so Secure Boot is disabled
while it runs. The Secure Boot keys stay enrolled and the preserved sbctl keys sign the new boot
chain, so Secure Boot is enabled again on the first boot of NixOS. Disabling Secure Boot changes
PCR 7: Windows must not boot until Secure Boot is enabled again, or BitLocker asks for its
recovery key.

All state carried over from Arch comes from one encrypted archive on the external T7 disk. The
archive is extracted once on the installer into a staging directory, copied to `/persist`, and
moved into the home directory after the first boot.

The installation downloads the inputs of the flake from GitHub and several GiB of packages from
the binary cache, so the installer needs network access from the start.

Lanzaboote does not register a boot entry in the firmware variables. Without an explicit entry,
the firmware boots the removable fallback loader of whichever disk comes first in its order, and
the entry left by Arch points at an EFI system partition that no longer exists. The procedure
creates the entry with `efibootmgr` and removes the stale one.

Two prompts must never compete for the same terminal. `sudo` and `age` both read the terminal; in
a pipeline they start together and split the typed input. Validate `sudo` first with `sudo -v`,
or work from a root shell.

## How to build the installer media

Blast radius: the USB key is overwritten entirely.

1. Build the image.

   ```bash
   nix build .#nixosConfigurations.installer.config.system.build.isoImage
   ```

2. Identify the USB key by its size and model.

   ```bash
   lsblk -o NAME,SIZE,MODEL,TRAN
   ```

3. Write the image to the key.

   ```bash
   sudo dd if=result/iso/<iso-file> of=/dev/<usb-device> bs=4M status=progress conv=fsync
   ```

   `<iso-file>` is the only file in `result/iso/`. `<usb-device>` is the whole device of the key,
   such as `sdb`, never a partition.

## How to prepare the switch

1. Push every commit of this repository.
2. Record the current boot measurements in the inventory.

   ```bash
   systemd-analyze pcrs 0 2 7 > inventory/pcrs-$(date +%F).txt
   ```

3. Check that the sbctl GUID file holds exactly 36 bytes, without a trailing newline.

   ```bash
   sudo wc -c /var/lib/sbctl/GUID
   ```

4. Create the archive on the T7 disk, then verify it by listing its directories.

   ```bash
   sudo -v
   sudo tar --create --zstd --xattrs --acls --file=- --exclude=rehearsal --exclude='result*' --exclude='*.qcow2' /var/lib/sbctl /etc/cryptsetup-keys.d /etc/NetworkManager/system-connections ~/.ssh ~/.config/nixos/ | nix run nixpkgs#age -- --passphrase --output "<t7-mount>/arch-backup-<date>.tar.zst.age"
   nix run nixpkgs#age -- -d "<t7-mount>/arch-backup-<date>.tar.zst.age" | tar --zstd -tf - | sed 's|/[^/]*$||' | sort -u
   ```

   `<t7-mount>` is the mount point of the T7 disk. The passphrase is stored in the password
   manager before the listing runs.

5. Plug the Ethernet cable.
6. Shut down, open the firmware setup, disable Secure Boot, and boot the USB key from the firmware
   boot menu. Do not boot Windows from this point until the switch is complete.

## How to install the system

Blast radius: every partition of the Linux NVMe disk is destroyed, including the Arch
installation. Rollback path: none for Arch; the state worth keeping is in the archive.

1. Open a root shell. The installer user has password-free `sudo`.

   ```bash
   sudo -i
   ```

2. Check network access. Without Ethernet, connect to Wi-Fi with `nmtui` first.

   ```bash
   ping -c1 github.com
   ```

3. Check that the target disk path designates the Linux disk and not the Windows disk.

   ```bash
   lsblk -o NAME,SIZE,MODEL,SERIAL
   ls -l /dev/disk/by-id/ | grep nvme
   ```

   The link named after the Samsung 990 PRO in `hosts/hephaestus/disko.nix` points at the disk
   whose model is the Samsung 990 PRO. Stop here if it does not.

4. Mount the T7 disk read-only, find the archive, and extract it into a staging directory.

   ```bash
   mkdir -p /mnt-t7 /tmp/restore
   mount -o ro /dev/<t7-partition> /mnt-t7
   ls /mnt-t7
   age -d "/mnt-t7/<archive-file>" | tar --zstd --xattrs --acls -xf - -C /tmp/restore
   ```

   `<t7-partition>` is the T7 partition shown by `lsblk`, such as `sda1`. `<archive-file>` is the
   archive listed by `ls`.

5. Partition, encrypt and mount the target disk. `disko` asks for the LUKS passphrase. A transient
   download error such as an HTTP 504 from GitHub is solved by running the command again.

   ```bash
   disko --mode destroy,format,mount --flake /tmp/restore/home/<arch-user>/.config/nixos#hephaestus
   ```

   `<arch-user>` is the user name of the Arch installation.

6. Restore the system state into the persistent subvolume. The BitLocker key file in
   `etc/cryptsetup-keys.d` is not restored.

   ```bash
   mkdir -p /mnt/persist/var/lib /mnt/persist/etc/NetworkManager
   cp -a /tmp/restore/var/lib/sbctl /mnt/persist/var/lib/
   cp -a /tmp/restore/etc/NetworkManager/system-connections /mnt/persist/etc/NetworkManager/
   cp -a /tmp/restore /mnt/persist/restore
   chmod 700 /mnt/persist/restore
   ```

7. Write the user password hash. `mkpasswd` alone reads the password once, without confirmation,
   and root has no password: a typo locks the session. The commands below read it twice and write
   the hash only when both entries match.

   ```bash
   install -d -m 700 /mnt/persist/secrets
   read -rsp "Password: " first && echo && read -rsp "Again: " second && echo
   [ "$first" = "$second" ] && printf '%s' "$first" | mkpasswd -m yescrypt -s > /mnt/persist/secrets/mowsoon.hash
   unset first second
   chmod 600 /mnt/persist/secrets/mowsoon.hash
   ```

8. Expose the sbctl keys at the path lanzaboote reads during the installation.

   ```bash
   mkdir -p /mnt/var/lib/sbctl
   mount --bind /mnt/persist/var/lib/sbctl /mnt/var/lib/sbctl
   ```

9. Install the system.

   ```bash
   nixos-install --flake /tmp/restore/home/<arch-user>/.config/nixos#hephaestus --no-root-password --no-channel-copy
   ```

10. Register the boot entry, then delete the entry left by Arch.

    ```bash
    efibootmgr --create --disk /dev/disk/by-id/<target-disk> --part 1 --label "Linux Boot Manager" --loader '\EFI\systemd\systemd-bootx64.efi'
    efibootmgr
    efibootmgr --bootnum <stale-entry> --delete-bootnum
    ```

    `<target-disk>` is the by-id link name of the Samsung 990 PRO shown at step 3. `<stale-entry>`
    is the four-digit number of the Arch entry shown by `efibootmgr`, distinct from the new entry
    and from `Windows Boot Manager`.

11. Unmount everything, remove the USB key and reboot.

    ```bash
    umount -R /mnt
    umount /mnt-t7
    reboot
    ```

## How to complete the first boot

1. Unlock the disk with the LUKS passphrase and log in.
2. Move the user files out of the staging directory, then delete it. The staging directory only
   holds hidden directories, so list it with `sudo ls -A`.

   ```bash
   sudo cp -a /persist/restore/home/<arch-user>/.ssh ~/
   mkdir -p ~/.config
   sudo cp -a /persist/restore/home/<arch-user>/.config/nixos ~/.config/
   sudo chown -R mowsoon:users ~/.ssh ~/.config/nixos
   sudo rm -rf /persist/restore
   ```

3. Check the signatures of the boot files.

   ```bash
   sudo sbctl verify
   ```

   `BOOTX64.EFI`, `systemd-bootx64.efi` and every image under `/boot/EFI/Linux/` are signed. The
   kernels under `/boot/EFI/nixos/` are expected unsigned: the signed image embeds their hash.

4. Reboot into the firmware setup, enable Secure Boot, and boot NixOS. Verify the state.

   ```bash
   sudo bootctl status
   ```

   `Secure Boot: enabled (user)` is expected.

5. Boot Windows once from the firmware boot menu. BitLocker opens without its recovery key.
6. Enroll the recovery key, the TPM2 slot and the header backup, following
   [LUKS enrollment](luks-enrollment.md).
7. Run the hardware checks listed in the reference below.
8. Delete the archive from the T7 disk.

## How to rehearse the installation

1. Commit the state to rehearse. The rehearsal archive contains a copy of `HEAD`.
2. Start from a blank state and boot the rehearsal machine. The first run asks for a test
   passphrase for the rehearsal archive.

   ```bash
   rm -rf rehearsal
   nix run .#rehearsal
   ```

3. Follow [How to install the system](#how-to-install-the-system) with the substitutions listed in
   the reference below.
4. Follow [How to complete the first boot](#how-to-complete-the-first-boot) without steps 5, 6
   and 8. Step 6 is covered by the `hephaestus-vm` machine. Before step 4, enroll the test keys.
   The rehearsal firmware enables Secure Boot by itself on the next boot, so step 4 reduces to a
   reboot followed by the verification.

   ```bash
   sudo sbctl enroll-keys --microsoft
   sudo reboot
   ```

5. Run only the hardware checks marked as applicable to the rehearsal.
6. Record every deviation between this document and the rehearsal, and fix this document.

## Reference

### Archive layout

| Directory in the archive | Destination |
| --- | --- |
| `var/lib/sbctl` | `/persist/var/lib/sbctl` |
| `etc/NetworkManager/system-connections` | `/persist/etc/NetworkManager/system-connections` |
| `etc/cryptsetup-keys.d` | Not restored |
| `home/<arch-user>/.ssh` | `~/.ssh` |
| `home/<arch-user>/.config/nixos` | `~/.config/nixos` |

### Rehearsal substitutions

| Item | Workstation | Rehearsal |
| --- | --- | --- |
| Target disk model and serial | Samsung 990 PRO | `QEMU NVMe Ctrl`, serial `rehearsal` |
| Target disk by-id link name | `nvme-Samsung_SSD_990_PRO_1TB_<serial>` | `nvme-QEMU_NVMe_Ctrl_rehearsal` |
| Flake output | `#hephaestus` | `#hephaestus-rehearsal` |
| T7 device | `/dev/sda1`, exFAT partition | `/dev/sda`, FAT image without a partition table |
| Archive file | `arch-backup-<date>.tar.zst.age` | `arch-backup-rehearsal.tar.zst.age` |
| `<arch-user>` | User name of the Arch installation | Host user that generated the rehearsal archive |
| Stale Arch boot entry | Present, deleted at install step 10 | Absent, the deletion is skipped |
| Secure Boot keys | Preserved keys, already enrolled | Test keys, enrolled after the first boot |

### Hardware checks

| Check | Command or action | Rehearsal |
| --- | --- | --- |
| Discrete GPU drives the session | `nvidia-smi` | No |
| ASUS daemon answers | `asusctl profile get` | No |
| Bluetooth adapter present | `bluetoothctl show` | No |
| Wi-Fi through iwd | `nmcli device wifi list` | No |
| BitLocker volume opens read-only | `sudo systemctl start mnt-windows.mount` | No |
| GPU inside a container | `sudo docker run --rm --device nvidia.com/gpu=all ubuntu nvidia-smi` | No |
| Hibernation resumes the session | `systemctl hibernate` | No |
| Nix fixed-output builds pass OpenSnitch | See the command below the table | Yes |
| No boot entry targets the Windows disk | `sudo bootctl list` | Yes |
| Firmware boots the registered entry | `sudo bootctl status` lists `Linux Boot Manager` as `active, boot-order` | Yes |
| Initrd modules match the hardware scan | `sudo nixos-generate-config --show-hardware-config` | Yes |
| PCR set chosen from the recorded measurements | Compare the files in `inventory/` | No |

`nixos-generate-config` prints one `ERROR: Not a Btrfs subvolume` line per impermanence bind
mount before the configuration. These lines are expected.

The fixed-output build check downloads a page with a deliberately wrong hash, so the build always
runs instead of reusing a cached result.

```bash
nix build --impure --expr 'let pkgs = (builtins.getFlake "nixpkgs").legacyPackages.x86_64-linux; in pkgs.fetchurl { url = "https://example.com"; hash = pkgs.lib.fakeHash; }'
```

A `hash mismatch in fixed-output derivation` error proves that the download went through. A
`Could not resolve host` error means that OpenSnitch blocked the builder.
