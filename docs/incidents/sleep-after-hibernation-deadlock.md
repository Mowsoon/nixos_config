# Sleep after hibernation deadlock

## Overview

Twice, the first sleep after a resume from hibernation never came back, and the only way out was
a forced power-off:

- On 2026-10-19, an idle "sleep, then hibernate" started from Plasma hung before the system went
  to sleep. The kernel reported `systemd-logind` and `chvt` blocked for minutes, and systemd
  killed logind on its watchdog without effect.
- On 2026-10-21, after powering on from hibernation on battery and leaving the lock screen, Plasma
  started a new sleep 30 seconds later. The journal ends at `PM: suspend entry (s2idle)`, and the
  machine did not wake up.

Over the same days, every sleep that did not follow a hibernation resumed correctly.

Affected configuration:

| Component | Version |
| --- | --- |
| nixpkgs | `nixos-unstable`, October 2026 |
| Kernel | `linuxPackages_zen`, 7.2.9 |
| NVIDIA driver | 595.104.02, open kernel modules, `kernelSuspendNotifier = false`, `NVreg_EnableS0ixPowerManagement = 1` |
| Desktop | Plasma 6, KWin on Wayland, discrete GPU only through the MUX |
| systemd | 261.3 |

Cause of the 2026-10-19 hang, read from the kernel hung task report: the driver loads with
runtime D3 enabled by default (`DynamicPowerManagement: 3`), so it powers the GPU down while the
panel is off. Before sleep, `nvidia-sleep.sh` switches to virtual terminal 63 with `chvt`.
`systemd-logind` completes the switch and, holding the console lock, unblanks the framebuffer
console. The resulting mode set needs the GPU, whose runtime resume
(`rm_transition_dynamic_power`) takes the console lock again. The task waits on itself, and
`chvt` and the runtime power management worker wait behind it:

```text
console_lock
rm_transition_dynamic_power [nvidia]
nv_pmops_runtime_resume [nvidia]
...
nvRmSetGc6Allowed [nvidia_modeset]
...
fbcon_blank
do_unblank_screen
complete_change_console
vt_ioctl
```

The 2026-10-21 hang left no trace: kernel messages written during sleep never reach the journal.
It happened in the same situation, the GPU idle behind a locked and blanked screen at the first
sleep after a hibernation resume, and is attributed to the same runtime D3 path without proof.

The Wi-Fi error `mt7921e ... pci_pm_restore returns -110`, logged on every hibernation resume, is
not the cause: the driver reloads its firmware right after, and sleeps that followed it resumed
correctly.

Resolution: `modules/hardware/nvidia.nix` sets
`hardware.nvidia.moduleParams.nvidia.NVreg_DynamicPowerManagement = 0`. With the MUX set to the
discrete GPU, the GPU drives the panel whenever the screen is on, so runtime D3 only applied
while the screen was off and saved nothing that matters next to sleep and hibernation.

Findings that narrowed the cause:

| Observation | Conclusion |
| --- | --- |
| Hung task report of 2026-10-19 | The NVIDIA runtime resume takes the console lock already held by the console switch |
| `DynamicPowerManagement: 3` in `/proc/driver/nvidia/params` | Runtime D3 was enabled by the driver default, not by the configuration |
| Two failures out of four sleeps that followed a hibernation resume, none on other sleeps | The failure needs the GPU state left after a hibernation resume and a blanked screen |
| Wi-Fi recovers after its restore error, and later sleeps succeed | The `mt7921e` error is unrelated |

The driver reads its options only when it is loaded. The fix takes effect after
`nixos-rebuild boot` and a real reboot, never after a resume from hibernation.

## How to verify the fix

1. Confirm the running system is the latest generation. Both paths must be identical.

   ```bash
   readlink /run/booted-system /nix/var/nix/profiles/system
   ```

2. Confirm the driver no longer uses runtime D3.

   ```bash
   grep 'DynamicPowerManagement:' /proc/driver/nvidia/params
   ```

   ```text
   DynamicPowerManagement: 0
   ```

3. Hibernate, power on, and leave the lock screen untouched until the screen turns off.

   ```bash
   systemctl hibernate
   ```

4. Start a sleep, wait one minute, then wake the machine.

   ```bash
   systemctl suspend-then-hibernate
   ```

5. Confirm the boot recorded no blocked task. The command must print nothing.

   ```bash
   journalctl -b 0 -k | grep 'blocked for more than'
   ```

## If the hang comes back

1. Before forcing the power-off, try a text console with `Ctrl+Alt+F3`.
2. After the next boot, look for blocked tasks and read the end of the failed boot.

   ```bash
   journalctl -b -1 -k | grep -A 60 'blocked for more than'
   ```

   ```bash
   journalctl -b -1 | tail -200
   ```

## Reference

| Source | Content |
| --- | --- |
| [NVIDIA 595.104.02 README, dynamic power management](https://download.nvidia.com/XFree86/Linux-x86_64/595.104.02/README/dynamicpowermanagement.html) | `NVreg_DynamicPowerManagement` values and defaults |
| [NVIDIA 595.104.02 README, power management](https://download.nvidia.com/XFree86/Linux-x86_64/595.104.02/README/powermanagement.html) | `nvidia-sleep.sh` and the console switch before sleep |
| [Linux kernel, runtime power management](https://docs.kernel.org/power/runtime_pm.html) | Runtime suspend and resume of devices |
| [Linux kernel, hung task detection](https://docs.kernel.org/admin-guide/sysctl/kernel.html#hung-task-timeout-secs) | `hung_task_timeout_secs` and the blocked task report |
