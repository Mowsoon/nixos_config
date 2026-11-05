# LUKS enrollment

## Overview

The root container is created by disko with a single passphrase slot. Four
operations cannot live in the repository because each one produces a secret or
a TPM2 object bound to one physical machine: the recovery key, the pcrlock
policy and its recovery PIN, the TPM2-sealed key and the header backup. They run
once, by hand, after installation and after the Secure Boot keys are final.

The TPM2 slot is bound to two policies at once: the systemd-pcrlock policy of
the NV index, which allows the firmware code measured in PCR 0, and the literal
value of PCR 7, which measures the Secure Boot state and keys. The
[firmware code lock](../architecture/boot-chain.md#firmware-code-lock) explains
the pcrlock policy. Enrolling or replacing Secure Boot keys changes PCR 7, so
the TPM2 slot is always enrolled last, after the pcrlock policy exists. The
`tpm2-device=auto` crypttab option, declared in `modules/security/luks.nix`,
makes the initrd try the TPM2 slot before asking for a passphrase.

The recovery PIN rewrites the pcrlock policy when it no longer matches the
running firmware. Together with a firmware able to forge PCR 7, it opens the
container, so it is kept like the recovery key, outside the machine.

The enrollment and the recovery from a failed unseal are replayed on a virtual
machine by the [failure drills](failure-drills.md).

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

## How to create the pcrlock policy

Prerequisites: `custom.pcrlock.enable` is applied, and the machine runs the
firmware to trust, booted normally.

1. Check that the firmware code of this boot was recorded. The unit is active
   and the file exists.

   ```bash
   systemctl status systemd-pcrlock-firmware-code.service
   sudo ls /var/lib/pcrlock.d/250-firmware-code-early.pcrlock.d
   ```

2. Allocate the NV index and write the policy. The command prints the recovery
   PIN once.

   ```bash
   sudo pcrlock-make-policy --recovery-pin=show
   ```

   The output lists `PCRs in protection mask: 0 (platform-code)`. Only
   `pcrlock-make-policy` writes the policy: `systemd-pcrlock make-policy`
   without its arguments would also lock PCR 11, which changes at every
   generation.

3. Store the PIN next to the recovery key in the password manager.

## How to enroll the TPM2

Prerequisites: Secure Boot is enabled with its final keys, the recovery key is
enrolled and the pcrlock policy exists.

1. Seal a new key against the pcrlock policy and PCR 7. The command asks for
   the passphrase or the recovery key.

   ```bash
   sudo systemd-cryptenroll /dev/disk/by-partlabel/disk-main-luks --tpm2-device=auto --tpm2-pcrlock=/var/lib/systemd/pcrlock.json --tpm2-pcrs=7
   ```

2. Reboot. The container opens without a passphrase prompt.
3. Verify the `systemd-tpm2` token. The plain `luksDump` output names the token
   without its policy, so read the JSON metadata instead.

   ```bash
   sudo cryptsetup luksDump --dump-json-metadata /dev/disk/by-partlabel/disk-main-luks | jq '.tokens'
   ```

   The `systemd-tpm2` token shows `"tpm2-pcrs": [ 7 ]` and
   `"tpm2_pcrlock": true`.

## How to replace an enrolled TPM2 slot

Blast radius: the TPM2 slot is replaced; until the new one is enrolled, the
container asks for the passphrase or the recovery key at boot. Rollback path:
the passphrase and the recovery key still open the container, and the previous
enrollment can be repeated.

1. Remove the TPM2 slot. The passphrase and the recovery key slots stay.

   ```bash
   sudo systemd-cryptenroll /dev/disk/by-partlabel/disk-main-luks --wipe-slot=tpm2
   ```

2. Enroll the new slot as in [How to enroll the TPM2](#how-to-enroll-the-tpm2).

The two commands stay separate. Combined in one call, `systemd-cryptenroll`
compares the requested policy with the existing slot; after a TPM clear the PCR
values are unchanged, so it reports that the PCR set is already enrolled and
does nothing, leaving a slot sealed to the old TPM.

## How to recover from a failed TPM2 unseal

1. At the passphrase prompt, type the recovery key instead of the passphrase.
2. Once booted, read why the unseal failed, and the state of the policy update.

   ```bash
   journalctl -b -o cat --unit systemd-cryptsetup@cryptroot.service
   systemctl status systemd-pcrlock-make-policy.service
   ```

3. Find the cause in the [unseal failures](#unseal-failures) table and apply
   its fix.

## How to accept the running firmware

Blast radius: the pcrlock policy is rewritten to allow the firmware that is
running, and only it. Rollback path: none needed, the TPM2 slot is unchanged.

Prerequisites: the firmware change is explained, for example by an update whose
version `/sys/class/dmi/id/bios_version` shows and the vendor publishes. An
unexplained change of PCR 0 is a firmware that nobody installed on purpose.

1. Rewrite the policy with the recovery PIN. The command asks for it.

   ```bash
   sudo pcrlock-make-policy --recovery-pin=query
   ```

2. Reboot. The container opens without a passphrase prompt.

## How to recreate the pcrlock policy after a TPM clear

A TPM clear deletes the NV index, so the policy file describes an index that no
longer exists. The policy update of every boot still reports that the
prediction is unchanged: only the unseal message shows the clear.

1. Remove the stale policy file and its copy on the ESP.

   ```bash
   sudo systemd-pcrlock remove-policy
   ```

   The command fails to remove the NV index, which the clear already deleted,
   and exits with an error after removing both files. Check that
   `/var/lib/systemd/pcrlock.json` is gone.

2. Create a new policy as in
   [How to create the pcrlock policy](#how-to-create-the-pcrlock-policy). It has
   a new recovery PIN; replace the old one in the password manager.
3. Replace the TPM2 slot as in
   [How to replace an enrolled TPM2 slot](#how-to-replace-an-enrolled-tpm2-slot).

## Reference

### Slots

| Slot | Unlocks with | Created by |
| --- | --- | --- |
| Passphrase | Typed passphrase | disko at format time |
| Recovery | 256-bit key printed once | `systemd-cryptenroll --recovery-key` |
| TPM2 | Key sealed against the pcrlock policy and PCR 7 | `systemd-cryptenroll --tpm2-device=auto --tpm2-pcrlock=` |

### Unseal failures

| Cause | Unseal message | Policy update | Fix |
| --- | --- | --- | --- |
| Firmware code changed (PCR 0) | `TPM policy does not match current system state`, ending with `Remote address changed` | Failed: `Failed to submit AuthorizeNV policy` | [Accept the running firmware](#how-to-accept-the-running-firmware), once the change is explained; a planned update is prepared as in [Firmware update](firmware-update.md) |
| Secure Boot state or keys changed (PCR 7), such as a dbx update | `TPM policy does not match current system state`, ending with `Operation not permitted` | Succeeds: `Prediction is identical to current policy` | [Replace the TPM2 slot](#how-to-replace-an-enrolled-tpm2-slot) |
| TPM cleared | `TPM key integrity check failed` | Succeeds: `Prediction is identical to current policy` | [Recreate the pcrlock policy](#how-to-recreate-the-pcrlock-policy-after-a-tpm-clear) |
