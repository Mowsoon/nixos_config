# Hibernation power-off hang

## Overview

On 2026-10-17, `systemctl hibernate` blanked the screen but the laptop never
powered off. After a forced power-off, the next boot resumed the session
intact, so the hibernation image was written completely. Only the final power
cut failed. A normal `systemctl poweroff` worked.

Affected configuration:

| Component | Version |
| --- | --- |
| nixpkgs | `26.11.20261006.151fa4e` (`nixos-unstable`) |
| Kernel | `linuxPackages_zen`, 7.2.9 |
| NVIDIA driver | 595.104.02, open kernel modules, `hardware.nvidia.powerManagement.enable = true` |
| systemd | 261.3 |

Cause: from driver 595 with the open kernel modules, the nixpkgs NVIDIA module
enables `hardware.nvidia.powerManagement.kernelSuspendNotifier` by default. The
driver is then loaded with `NVreg_UseKernelSuspendNotifiers=1` and reacts to
kernel suspend and hibernation events itself. The systemd units
`nvidia-suspend`, `nvidia-hibernate` and `nvidia-resume` are no longer
installed. With this path, the machine hangs after writing the hibernation
image. The exact device callback that blocks is not identified: kernel
messages emitted after the memory snapshot are never stored in the journal,
because resume restores the memory as it was before the snapshot.

Resolution: `modules/hardware/nvidia.nix` sets
`hardware.nvidia.powerManagement.kernelSuspendNotifier = false`. The driver is
loaded without `NVreg_UseKernelSuspendNotifiers`, and the systemd units run
`nvidia-sleep.sh` before hibernation and after resume, as with drivers older
than 595. Video memory preservation (`NVreg_PreserveVideoMemoryAllocations=1`)
stays enabled.

Findings that narrowed the cause:

| Test | Result | Conclusion |
| --- | --- | --- |
| Normal power-off | Works | The hang is specific to the hibernation path |
| Resume after a forced power-off | Session restored | The image is written in full; the hang is at the final power cut |
| `HibernateMode=shutdown` drop-in in `/run/systemd/sleep.conf.d/` | Same hang | The ACPI platform hibernation method is not the cause |
| Unloading the Wi-Fi driver `mt7921e` before hibernating | Same hang | The Wi-Fi driver is not the cause, despite its `pci_pm_restore returns -110` error on every resume |
| `kernelSuspendNotifier = false`, after a real reboot | Powers off, resumes correctly | The NVIDIA kernel suspend notifier path is the cause |

A test of a kernel or driver option requires a real reboot. Powering on after
a hibernation resumes the image, which holds the previous kernel and the
previous module options, even when `nixos-rebuild boot` has installed a new
generation. The first run of the NVIDIA test was invalid for this reason.

The rarer failures seen after this fix, on 2026-10-21 and 2026-10-22, have a different cause:
[hibernation-input-wakeup-hang](hibernation-input-wakeup-hang.md).

## How to verify the fix

1. Confirm the running system is the latest generation. Both paths must be
   identical.

   ```bash
   readlink /run/booted-system /nix/var/nix/profiles/system
   ```

2. Confirm the driver does not use kernel suspend notifiers.

   ```bash
   grep UseKernelSuspendNotifiers /proc/driver/nvidia/params
   ```

   ```text
   UseKernelSuspendNotifiers: 0
   ```

3. Hibernate, wait for the machine to power off, then power it on.

   ```bash
   systemctl hibernate
   ```

4. Confirm the NVIDIA units ran around the hibernation.

   ```bash
   journalctl -b 0 -u nvidia-hibernate -u nvidia-resume
   ```

## How to check whether the workaround is still needed

Run this after a NVIDIA driver or kernel update.

1. Remove `kernelSuspendNotifier = false;` from `modules/hardware/nvidia.nix`.
2. Build and install the generation as the next boot entry.

   ```bash
   nixos-rebuild boot --flake ~/.config/nixos#hephaestus --elevate sudo
   ```

3. Reboot with `systemctl reboot`, never by resuming from hibernation.
4. Confirm `UseKernelSuspendNotifiers: 1` in `/proc/driver/nvidia/params`.
5. Hibernate and wait two minutes.
6. If the machine powers off, keep the change. Otherwise force the power-off,
   restore the line, and run `nixos-rebuild boot` and a reboot again.

## Reference

| Source | Content |
| --- | --- |
| [NVIDIA 595.104.02 README, power management](https://download.nvidia.com/XFree86/Linux-x86_64/595.104.02/README/powermanagement.html) | `NVreg_UseKernelSuspendNotifiers`, video memory preservation, systemd configuration |
| [NixOS options search](https://search.nixos.org/options?query=hardware.nvidia.powerManagement) | `hardware.nvidia.powerManagement.enable` and `kernelSuspendNotifier` |
| [nixpkgs NVIDIA module](https://github.com/NixOS/nixpkgs/blob/nixos-unstable/nixos/modules/hardware/video/nvidia.nix) | Default of `kernelSuspendNotifier`, units and module options it generates |
| [Linux kernel, debugging hibernation and suspend](https://docs.kernel.org/power/basic-pm-debugging.html) | `/sys/power/disk` modes, `pm_test`, console debugging |
| [systemd-sleep.conf(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd-sleep.conf.html) | `HibernateMode` and drop-in directories |
