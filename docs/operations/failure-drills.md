# Failure drills

## Overview

A recovery path that has never run is a hope, not a procedure. Each drill breaks the boot chain of
a throwaway machine on purpose and asserts that the documented recovery brings it back. The drills
are NixOS VM tests: Nix builds the machine, boots it in QEMU, and a Python script drives it through
the serial console and asserts every step. A drill passes when its build succeeds. Kernel messages
share the serial console with the passphrase prompt and can cut it in the middle of a word, more
than once, so the drills recognize the prompt by any of three short pieces of it.

The drill machine is not the full workstation. It imports the modules of the boot chain only: the
disko layout of `hephaestus`, Secure Boot through lanzaboote, the LUKS2 container with its TPM2
unlock, its systemd-pcrlock firmware lock and its PCR 12 credentials lock, the root rollback, the
persistence and envfs, whose initrd rule keeps `/usr` valid on the empty root, plus `tpm2-tools`,
`efitools` and `openssl` to break the TPM and the firmware databases. Desktop, NVIDIA and Home
Manager are left out, so the disk image stays small and a drill does not rebuild the KWin graft.
The VM settings it shares with `hephaestus-vm` live in `hosts/hephaestus/vm.nix`: OVMF firmware
with Secure Boot support, an emulated TPM (swtpm), and Secure Boot keys generated at first boot
and enrolled by systemd-boot.

Every drill starts from a fresh copy-on-write overlay of the disko image, a blank firmware variable
store and a blank TPM. The firmware variables and the TPM state survive a crash and a restart
inside one drill, as they would on the hardware. The LUKS passphrase of the image is `disko`, the
fixed passphrase disko uses for test images.

Most drills start from a provisioned machine, the state of the workstation after installation:
the first boot has enrolled the Secure Boot keys, then the recovery key, the pcrlock policy and
the TPM2 slot bound to it, to PCR 7 and to PCR 12 are enrolled as in
[LUKS enrollment](luks-enrollment.md). The `enrollment` drill asserts that state, so the manual
procedure is a regression test.

The `rebuild-power-loss` drill needs a power cut at an exact moment of a rebuild, a window of
milliseconds. A crash ordered from the host by the test driver arrives too late, so the machine
cuts itself: a transient service loops on a condition, such as a file appearing on the ESP, then
writes `b` to `/proc/sysrq-trigger`, which restarts the kernel at once without syncing or
unmounting any filesystem. The drill machine carries a second system, identical except for the
file `/etc/drill-generation`, so a rebuild has a new generation to install without downloading
anything.

The `firmware-update` drill needs a firmware whose code differs. The drill machine carries a second
VM start script, identical except for an OVMF build without HTTP boot; the drill swaps the start
command of the machine between two boots, and the disk, the firmware variables and the TPM state
carry over, as they would across a firmware update.

The drills are flake checks named `drill-<name>`. Nix caches a passed drill and runs it again only
when one of its inputs changes: nixpkgs, disko, lanzaboote, impermanence or one of the imported
modules. After a `nix flake update`, the first `nix flake check` therefore runs every drill.

## How to run a drill

1. Build the drill. The `-L` flag prints the log of the VM, including its serial console.

   ```bash
   nix build -L .#checks.x86_64-linux.drill-<name>
   ```

   `<name>` is a drill of the Reference table, such as `boot`.

2. A failed assertion stops the build with the Python traceback and the console output. A passed
   drill builds without output; add `--rebuild` to run it again despite the cache.

## How to drive a drill by hand

1. Open the interactive driver of the drill. It builds the machine without starting it and opens
   a Python prompt.

   ```bash
   nix run .#checks.x86_64-linux.drill-<name>.driverInteractive
   ```

   `<name>` is a drill of the Reference table.

2. Run the whole script with `test_script()`, or type its lines one by one, such as
   `machine.start(allow_reboot=True)` or `unlock_with_passphrase()`. The helpers of
   `tests/drills/helpers.py` are loaded before the prompt opens.
3. Leave with `Ctrl+D`. The overlay disk, the firmware variables and the TPM state stay in
   `/tmp/vm-state-machine` until the next start of the driver, which deletes them.

## Reference

| Drill | Breaks | Expected | Observed |
| --- | --- | --- | --- |
| `boot` | Nothing on first boot, then the power during a running system | Keys generated and enrolled, Secure Boot in user mode; after the power loss, the root is empty, `/persist` keeps its files and the keys are not generated again | Passed on 2026-11-01 in 80 s: two passphrase prompts on first boot (before and after the enrollment reboot), Secure Boot in user mode, root marker gone and `/persist` marker kept after the crash |
| `credential-injection` | The ESP: a `tmpfiles.extra.cred` file dropped into `loader/credentials` | PCR 12 changes at the next boot, the unseal fails and the recovery key opens the container; the reseal of that boot refuses the unknown credential, fails the policy update unit and records it in `/run/pcr12/alert`, and the slot is left unchanged; once the file is removed, the next boot is unattended again with the sealed PCR 12 | Passed on 2026-11-05 in 152 s: the unseal fails with `Operation not permitted`, the reseal stops with `the ESP must hold only the pcrlock credential, found` and both file names, the token keeps `tpm2-pcrs` `[7, 12]`. A first run failed: `pcrlock.json` ends with a newline that its ESP copy lacks, so the copy is compared without the final newline |
| `dbx-update` | The firmware forbidden signature database: a throwaway certificate appended to dbx, signed with the KEK from the running system as Windows Update does | PCR 7 changes at the next boot, the unseal fails and the recovery key opens the container; the pcrlock policy still matches, but the reseal of that boot cannot unlock with the current slot, fails the policy update unit and records it in `/run/pcr12/alert`; `pcr12 reseal --ask-key` with the recovery key restores the unattended boot, Secure Boot still in user mode | Passed on 2026-11-05 in 133 s with the slot sealed to PCR 7 and PCR 12: the unseal fails with `Operation not permitted`, the reseal stops with `the TPM2 slot no longer unlocks the container`, and the single reseal call enrolls the new slot and wipes the old one. On 2026-11-04, with the pcrlock slot alone, the wipe-then-enroll procedure was used |
| `enrollment` | Nothing: replays [LUKS enrollment](luks-enrollment.md) on the provisioned machine | The policy update unit skipped before the policy exists; the reseal run by the policy creation does nothing before the first TPM2 slot; a `systemd-recovery` token and a `systemd-tpm2` token bound to the pcrlock policy, PCR 7 and PCR 12; the next boot opens the container without a passphrase prompt and the policy update succeeds, Secure Boot still in user mode | Passed on 2026-11-05 in 92 s: both tokens present, `tpm2-pcrs` is `[7, 12]` and `tpm2_pcrlock` is `true` in the JSON metadata, no prompt on the next boot. The plain `luksDump` output does not list the policy |
| `firmware-update` | The firmware code: the machine boots on a second OVMF build without HTTP boot, whose PCR 0 differs | With a TPM2 slot bound to the pcrlock policy of PCR 0, to PCR 7 and to PCR 12: the unseal fails on the other firmware and its policy update is refused; back on the first firmware the unchanged policy unseals; a variant of the other firmware added before the switch keeps the unattended boot; once that firmware is locked alone, the first one fails; the recovery PIN then locks the running firmware and the next boot is unattended. Every policy write renews the slot for the new policy copy without any manual step | Passed on 2026-11-05 in 255 s: each policy write is followed by `sealed the TPM2 slot to PCR 7 and PCR 12`, and every boot after one opens without a prompt. A first run on 2026-11-04 expected the boot-time lock to accept the firmware unlocked with the recovery key: the update is refused, because the generated PIN is sealed to the policy it would replace. The index is therefore created by hand with a PIN shown once |
| `generation-lock` | The generation and `loader.conf`, with a pcrlock policy over PCRs 0, 5 and 11: a rebuild to the second generation, a boot of the first from `bootctl set-oneshot`, then `loader.conf` edited by hand | Each installed generation unseals: the install hook writes the PCR 11 variant of the new stub and rewrites the policy before the reboot; the edited `loader.conf` fails the unseal, the policy update of that boot is refused, and restoring the file brings the unattended boot back | Passed on 2026-11-06 in 202 s, after three fixes found by it: OVMF measures the GPT once and retries `ExitBootServices` after a failed call, so PCR 5 needs variants for both; pcrlock keeps the first matching variant by name, so the empty `ExitBootServices` variant must sort last; the boot menu hides the backdoor greeting on the console, so the drill sets `timeout 0` |
| `rebuild-power-loss` | The power during a rebuild: once while lanzaboote installs the stub of generation 2, once while `switch-to-configuration switch` activates generation 3 | A complete generation boots each time: generation 1 for the first cut, generation 3 for the second, whose stub was written and synced before the activation. Running the whole rebuild again, profile update included, leaves no temporary file on the ESP, every stub and systemd-boot signed, and boots the new generation | Passed on 2026-11-01 in 167 s. First cut 0.65 s into the install: the profile had lost the `system-2-link` written by `nix-env --set` just before, so running only `switch-to-configuration` again installed nothing new. Second cut: `system-3-link` survived. After each cut, `fsck.vfat` found the dirty bit of the ESP and removed it; no file was damaged |
| `sealed-keys` | The Secure Boot private keys: sealed to PCR 15 by `secure-boot-keys seal` and removed in plain text, then PCR 15 extended from the running system | A rebuild to the second generation signs its stub with the decrypted db key and leaves no `/run/secure-boot-keys`; the ESP is consistent and the second generation boots with Secure Boot in user mode; `secure-boot-keys sbctl` verifies the ESP and signs the PK, KEK and db updates with the decrypted keys, then leaves none behind; once PCR 15 holds another value, the keys no longer decrypt | Passed on 2026-11-07 in 95 s: the decryption fails with `TPM policy does not match current system state`. Two fixes found by it: the disk image is built before any key exists, so the hook installs unsigned when `/var/lib/sbctl` is empty; sbctl does not derive the key paths from `keydir`, so `sbctl.conf` names each key. The drill sets `timeout 0`, as `generation-lock` does. Until 2026-11-07 the ESP check of every drill passed without checking: once the plain db key is gone, `sbctl verify` prints `failed to verify` for every file and exits 0, so the check now runs `secure-boot-keys sbctl verify` and requires a signed stub |
| `sealed-keys-recovery` | The TPM, cleared with `tpm2_clear` once the keys are sealed and a plain recovery copy is kept in `/persist`, standing in for the T7 disk | The recovery key opens the container and PCR 15 is still measured, but the keys no longer decrypt, `secure-boot-keys unseal` leaves no partial `/run/secure-boot-keys`, and a rebuild fails before lanzaboote writes the stub of the new generation; after the pcrlock policy and the TPM2 slot are recreated, the recovery copy restored and sealed again, the profile generation installs signed and boots with the TPM2 slot | Passed on 2026-11-07 in 107 s: systemd-creds fails with `TPM key integrity check failed`, the rebuild ends with `Failed to install bootloader` and leaves the profile on the uninstalled generation 2, which the next install writes and signs |
| `tpm-clear` | The TPM, cleared from the running system with `tpm2_clear` | The unseal fails and the initrd asks for the passphrase or the recovery key; the recovery key opens the container; the procedure of [LUKS enrollment](luks-enrollment.md#how-to-recreate-the-pcrlock-policy-after-a-tpm-clear), run with the recovery key as the only secret, creates a new pcrlock policy, whose automatic reseal fails, then leaves one TPM2 token bound to it, to PCR 7 and to PCR 12, and the next boot is unattended | Passed on 2026-11-05 in 133 s: the unseal fails with a TPM key integrity error while the policy update and the reseal still report nothing to do, since the slot values are unchanged; `systemd-pcrlock remove-policy` cannot remove the deleted NV index and exits with an error, but removes the policy file and its ESP copy. The new policy copy changes PCR 12, so the single reseal call enrolls a new slot instead of reporting it already enrolled, as a PCR 7 slot did on 2026-11-01 |
| `volume-key` | Nothing: checks the measurement of the volume key of the root container into PCR 15 | PCR 15 is not zero after an unlock by the TPM2 slot, keeps its value at the next boot, and takes the same value after an unlock with the recovery key | Passed on 2026-11-06 in 139 s: `systemd-pcrextend` extends PCR 15 with `cryptsetup:cryptroot:<uuid>` in every bank, the same value at each boot, by the TPM2 slot or the recovery key |

| File | Content |
| --- | --- |
| `tests/drills/default.nix` | One flake check per drill script, built on the shared machine with the modules of the drill, such as the PCR list of `generation-lock` |
| `tests/drills/node.nix` | Drill machine: boot chain modules of `hephaestus`, the shared VM settings, the second generation used by `rebuild-power-loss` and the VM on a second OVMF build used by `firmware-update` |
| `tests/drills/helpers.py` | Overlay disk, passphrase and TPM2 boots, first boot with key enrollment, recovery key and TPM2 enrollment through `pcr12 reseal --ask-key`, pcrlock policy creation, recreation and TPM2 enrollment, recovery and slot replacement, token and PCR checks, refused reseal, power cut, booted entry, ESP check |
| `tests/drills/<name>.py` | Script of one drill |
| `hosts/hephaestus/vm.nix` | VM settings shared with `hephaestus-vm` |
