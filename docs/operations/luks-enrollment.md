# LUKS enrollment

## Overview

The root container is created by disko with a single passphrase slot. Four
operations cannot live in the repository because each one produces a secret or
a TPM2 object bound to one physical machine: the recovery key, the pcrlock
policy and its recovery PIN, the TPM2-sealed key and the header backup. They run
once, by hand, after installation and after the Secure Boot keys are final.

The TPM2 slot is bound to three measurements at once: the systemd-pcrlock
policy of the NV index, which allows the firmware code measured in PCR 0, the
literal value of PCR 7, which measures the Secure Boot state and keys, and the
literal value of PCR 12, which measures the credentials of the ESP. The
[firmware code lock](../architecture/boot-chain.md#firmware-code-lock) explains
the pcrlock policy, the
[credentials lock](../architecture/boot-chain.md#credentials-lock) why every
policy rewrite renews the slot by itself. Enrolling or replacing Secure Boot keys changes PCR 7, so
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
enrolled, the pcrlock policy exists, `custom.pcrlock.lockCredentials` is
applied, and `/boot/loader/credentials` holds only the `pcrlock.*.cred` policy
copy.

1. Seal a new key against the pcrlock policy, PCR 7 and the next PCR 12. The
   command asks for the passphrase or the recovery key.

   ```bash
   sudo pcr12 reseal --ask-key
   ```

   It refuses when the ESP holds another credential, or when `pcr12-check`
   did not reproduce PCR 12 at this boot.

2. Reboot. The container opens without a passphrase prompt.
3. Verify the `systemd-tpm2` token. The plain `luksDump` output names the token
   without its policy, so read the JSON metadata instead.

   ```bash
   sudo cryptsetup luksDump --dump-json-metadata /dev/disk/by-partlabel/disk-main-luks | jq '.tokens'
   ```

   The `systemd-tpm2` token shows `"tpm2-pcrs": [ 7, 12 ]` and
   `"tpm2_pcrlock": true`.

## How to replace an enrolled TPM2 slot

Blast radius: the TPM2 slot is replaced. Rollback path: the old slot is wiped
only once the new one is written, and the passphrase and the recovery key still
open the container.

1. Enroll the new slot, unlocked with the recovery key. The command asks for it.

   ```bash
   sudo pcr12 reseal --ask-key
   ```

2. Reboot. The container opens without a passphrase prompt.

`systemd-cryptenroll` does nothing when the requested policy equals the
enrolled one. A replacement is needed only after a change of PCR 7, or after a
TPM clear whose new pcrlock policy changes the copy measured in PCR 12, so the
requested policy always differs from the enrolled one.

## How to recover from a failed TPM2 unseal

1. At the passphrase prompt, type the recovery key instead of the passphrase.
2. Once booted, read why the unseal failed, and the state of the policy update.
   A failed policy update or reseal also shows a desktop notification at login.

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
unexplained change of PCR 0 is a firmware that nobody installed on purpose. The
same procedure accepts a generation, an option ROM, a partition table or a
`loader.conf` that the policy does not allow, once the change is explained.

1. Rewrite the policy with the recovery PIN. The command asks for it, then
   renews the TPM2 slot for the new policy copy.

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
   a new recovery PIN; replace the old one in the password manager. The command
   ends with an error: the slot it tries to renew was sealed by the cleared TPM
   and cannot unlock, so it asks for `pcr12 reseal --ask-key`.
3. Replace the TPM2 slot as in
   [How to replace an enrolled TPM2 slot](#how-to-replace-an-enrolled-tpm2-slot).

## Reference

### Slots

| Slot | Unlocks with | Created by |
| --- | --- | --- |
| Passphrase | Typed passphrase | disko at format time |
| Recovery | 256-bit key printed once | `systemd-cryptenroll --recovery-key` |
| TPM2 | Key sealed against the pcrlock policy, PCR 7 and PCR 12 | `pcr12 reseal`, after every policy change |

### Unseal failures

| Cause | Unseal message | Policy update | Fix |
| --- | --- | --- | --- |
| Firmware code changed (PCR 0) | `TPM policy does not match current system state`, ending with `Remote address changed` | Failed: `Failed to submit AuthorizeNV policy` | [Accept the running firmware](#how-to-accept-the-running-firmware), once the change is explained; a planned update is prepared as in [Firmware update](firmware-update.md) |
| Generation booted without its prediction (PCR 11): the install hook failed, or a stub was copied by hand | As for PCR 0 | Failed, as for PCR 0 | Check that the generation is the one built, then [accept the running state](#how-to-accept-the-running-firmware) with the recovery PIN, which also adds the generation |
| Option ROM at boot, partition table or `loader.conf` changed (PCR 2 or 5) | As for PCR 0 | Failed, as for PCR 0 | Explain the change: a device attached at boot, a repartition, a new `boot.loader` setting; then [accept the running state](#how-to-accept-the-running-firmware) |
| Secure Boot state or keys changed (PCR 7), such as a dbx update | `TPM policy does not match current system state`, ending with `Operation not permitted` | Failed: the prediction is identical, but the reseal cannot unlock with the current slot and asks for `pcr12 reseal --ask-key` | [Replace the TPM2 slot](#how-to-replace-an-enrolled-tpm2-slot) |
| Credential added to the ESP (PCR 12) | `TPM policy does not match current system state`, ending with `Operation not permitted` | Failed: `the ESP must hold only the pcrlock credential, found` and the file names | Find who wrote the extra file under `/boot/loader/credentials`, remove it, reboot: the slot was never resealed, so the unattended boot comes back |
| TPM cleared | `TPM key integrity check failed` | Succeeds: `Prediction is identical to current policy` | [Recreate the pcrlock policy](#how-to-recreate-the-pcrlock-policy-after-a-tpm-clear) |
