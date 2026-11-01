# Failure drills

## Overview

A recovery path that has never run is a hope, not a procedure. Each drill breaks the boot chain of
a throwaway machine on purpose and asserts that the documented recovery brings it back. The drills
are NixOS VM tests: Nix builds the machine, boots it in QEMU, and a Python script drives it through
the serial console and asserts every step. A drill passes when its build succeeds.

The drill machine is not the full workstation. It imports the modules of the boot chain only: the
disko layout of `hephaestus`, Secure Boot through lanzaboote, the LUKS2 container with its TPM2
unlock, the root rollback and the persistence. Desktop, NVIDIA and Home Manager are left out, so
the disk image stays small and a drill does not rebuild the KWin graft. The VM settings it shares
with `hephaestus-vm` live in `hosts/hephaestus/vm.nix`: OVMF firmware with Secure Boot support, an
emulated TPM (swtpm), and Secure Boot keys generated at first boot and enrolled by systemd-boot.

Every drill starts from a fresh copy-on-write overlay of the disko image, a blank firmware variable
store and a blank TPM. The firmware variables and the TPM state survive a crash and a restart
inside one drill, as they would on the hardware. The LUKS passphrase of the image is `disko`, the
fixed passphrase disko uses for test images.

Most drills start from a provisioned machine, the state of the workstation after installation:
the first boot has enrolled the Secure Boot keys, then the recovery key and the TPM2 slot sealed
against PCR 7 are enrolled as in [LUKS enrollment](luks-enrollment.md). The `enrollment` drill
asserts that state, so the manual procedure is a regression test.

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

| `enrollment` | Nothing: replays [LUKS enrollment](luks-enrollment.md) on the provisioned machine | A `systemd-recovery` token and a `systemd-tpm2` token sealed against PCR 7; the next boot opens the container without a passphrase prompt, Secure Boot still in user mode | Passed on 2026-11-01 in 91 s: both tokens present, `tpm2-pcrs` is `[7]` in the JSON metadata, no prompt on the next boot. The plain `luksDump` output does not list the PCRs |

| File | Content |
| --- | --- |
| `tests/drills/default.nix` | One flake check per drill script, built on the shared machine |
| `tests/drills/node.nix` | Drill machine: boot chain modules of `hephaestus` and the shared VM settings |
| `tests/drills/helpers.py` | Overlay disk, passphrase and TPM2 boots, first boot with key enrollment, recovery key and TPM2 enrollment |
| `tests/drills/<name>.py` | Script of one drill |
| `hosts/hephaestus/vm.nix` | VM settings shared with `hephaestus-vm` |
