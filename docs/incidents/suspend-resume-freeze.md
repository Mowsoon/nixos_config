# Suspend resume freeze

## Overview

On 2026-10-17, after an idle suspend triggered by Plasma, the laptop woke up
but the desktop never came back. The only way out was a forced power-off. The
same failure happened earlier on Arch Linux on the same machine. Hibernation
and resume from hibernation kept working.

Affected configuration:

| Component | Version |
| --- | --- |
| nixpkgs | `26.11.20261006.151fa4e` (`nixos-unstable`) |
| Kernel | `linuxPackages_zen`, 7.2.9 |
| NVIDIA driver | 595.104.02, open kernel modules, `hardware.nvidia.powerManagement.enable = true`, `kernelSuspendNotifier = false` |
| Desktop | Plasma 6, KWin on Wayland, discrete GPU only through the MUX |
| systemd | 261.3 |

Cause: the firmware only offers the `s2idle` sleep state (S0ix, modern
standby). `/sys/power/mem_sleep` lists `[s2idle]` and no `deep`. The NVIDIA
driver was loaded with `NVreg_EnableS0ixPowerManagement=0`, so it handled
`s2idle` as a full S3 suspend in which the GPU loses power. On resume, the
kernel, the disks and `nvidia-resume.service` all completed, then KWin flooded
the journal with these errors and stopped drawing:

```text
kwin_wayland: 0x502: GL_INVALID_OPERATION error generated. <image> and <target> are incompatible
kwin_wayland: Invalid framebuffer status:  "GL_FRAMEBUFFER_INCOMPLETE_ATTACHMENT"
```

Hibernation was not affected: resume from S4 boots a fresh kernel, which
initialises the GPU from scratch before restoring video memory.

Resolution: `modules/hardware/nvidia.nix` sets
`hardware.nvidia.moduleParams.nvidia.NVreg_EnableS0ixPowerManagement = 1`. The
driver then uses its S0ix path for `s2idle`, and the suspend path through the
`nvidia-suspend` and `nvidia-resume` systemd units is kept, as required by
[hibernation-power-off](hibernation-power-off.md).

Findings that narrowed the cause:

| Test | Result | Conclusion |
| --- | --- | --- |
| Journal of the failed resume | Kernel resume and `nvidia-resume.service` succeed, KWin GL errors start right after | The system wakes up; only the GPU state seen by KWin is broken |
| Resume from hibernation | Works | The failure is specific to `s2idle` |
| `SYSTEMD_SLEEP_FREEZE_USER_SESSIONS=false` on the sleep services, with `nixos-rebuild test` | Same freeze, journal confirms the sessions stayed unfrozen | Freezing of the user session before `nvidia-resume` is not the cause |
| `NVreg_EnableS0ixPowerManagement=1`, after a real reboot | Suspend and hibernation both resume to the desktop | The missing S0ix support in the driver is the cause |

The driver reads its options only when it is loaded. A test of this option
requires `nixos-rebuild boot` and a reboot; `nixos-rebuild test` is not enough.

## How to verify the fix

1. Confirm the running system is the latest generation. Both paths must be
   identical.

   ```bash
   readlink /run/booted-system /nix/var/nix/profiles/system
   ```

2. Confirm the driver uses S0ix power management.

   ```bash
   grep EnableS0ixPowerManagement /proc/driver/nvidia/params
   ```

   ```text
   EnableS0ixPowerManagement: 1
   ```

3. Suspend, wait one minute, then wake the machine.

   ```bash
   systemctl suspend
   ```

4. Confirm the resume left no KWin GL error. The command must print nothing.

   ```bash
   journalctl -b 0 | grep GL_FRAMEBUFFER_INCOMPLETE_ATTACHMENT
   ```

5. Hibernate and resume once, to check that
   [hibernation-power-off](hibernation-power-off.md) still holds.

## If the freeze comes back

1. Before forcing the power-off, try a text console with `Ctrl+Alt+F3`. If it
   opens, log in and run `nvidia-smi` to tell a GPU failure from a KWin
   failure.
2. After the next boot, read the end of the failed boot.

   ```bash
   journalctl -b -1 | tail -200
   ```

## Reference

| Source | Content |
| --- | --- |
| [NVIDIA 595.104.02 README, power management](https://download.nvidia.com/XFree86/Linux-x86_64/595.104.02/README/powermanagement.html) | `NVreg_EnableS0ixPowerManagement`, S0ix video memory threshold, video memory preservation |
| [nixpkgs NVIDIA module](https://github.com/NixOS/nixpkgs/blob/nixos-unstable/nixos/modules/hardware/video/nvidia.nix) | `hardware.nvidia.moduleParams` and the sleep units it generates |
| [Linux kernel, system sleep states](https://docs.kernel.org/admin-guide/pm/sleep-states.html) | `s2idle` versus `deep`, `/sys/power/mem_sleep` |
| [systemd-sleep.conf(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd-sleep.conf.html) | `SYSTEMD_SLEEP_FREEZE_USER_SESSIONS` |
