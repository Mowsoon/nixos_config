# LUKS enrollment

## Overview

The root container is created by disko with a single passphrase slot. Three
operations cannot live in the repository because each one produces a secret
bound to one physical machine: the recovery key, the TPM2-sealed key and the
header backup. They run once, by hand, after installation and after the Secure
Boot keys are final.

The TPM2 slot is sealed against Secure Boot policy measurements (PCR 7).
Enrolling or replacing Secure Boot keys changes PCR 7, so the TPM2 slot is
always enrolled last. The `tpm2-device=auto` crypttab option, declared in
`modules/security/luks.nix`, makes the initrd try the TPM2 slot before asking
for a passphrase.

## How to enroll the recovery key

Prerequisites: the system is booted and the container passphrase is known.

1. Enroll a recovery key. The command asks for the passphrase, then prints the
   key once.

   ```bash
   sudo systemd-cryptenroll /dev/disk/by-partlabel/disk-main-luks --recovery-key
   ```

2. Store the printed key in the password manager. It is never written to disk.
3. Verify that a `systemd-recovery` token exists.

   ```bash
   sudo cryptsetup luksDump /dev/disk/by-partlabel/disk-main-luks
   ```

## How to enroll the TPM2

Prerequisites: Secure Boot is enabled with its final keys and the recovery key
is enrolled.

1. Seal a new key against PCR 7.

   ```bash
   sudo systemd-cryptenroll /dev/disk/by-partlabel/disk-main-luks --tpm2-device=auto --tpm2-pcrs=7
   ```

2. Reboot. The container opens without a passphrase prompt.
3. Verify that a `systemd-tpm2` token exists and lists PCR 7.

   ```bash
   sudo cryptsetup luksDump /dev/disk/by-partlabel/disk-main-luks
   ```

## How to back up the header

Blast radius: none, the command only reads the device.

1. Write the header to a file on the ephemeral root.

   ```bash
   sudo cryptsetup luksHeaderBackup /dev/disk/by-partlabel/disk-main-luks --header-backup-file /root/luks-header.img
   ```

2. Copy the file to the password manager as an attachment, then delete it.

   ```bash
   sudo rm /root/luks-header.img
   ```

## How to recover from a failed TPM2 unseal

1. At the passphrase prompt, type the recovery key instead of the passphrase.
2. Once booted, read the current Secure Boot policy measurement.

   ```bash
   systemd-analyze pcrs 7
   ```

3. Replace the stale TPM2 slot with a new one sealed against the current state.

   ```bash
   sudo systemd-cryptenroll /dev/disk/by-partlabel/disk-main-luks --wipe-slot=tpm2 --tpm2-device=auto --tpm2-pcrs=7
   ```

## Reference

| Slot | Unlocks with | Created by |
| --- | --- | --- |
| Passphrase | Typed passphrase | disko at format time |
| Recovery | 256-bit key printed once | `systemd-cryptenroll --recovery-key` |
| TPM2 | Key sealed against PCR 7 | `systemd-cryptenroll --tpm2-device=auto` |
