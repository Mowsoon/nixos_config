# Sleep after hibernation deadlock

## Overview

The first sleep after a resume from hibernation failed repeatedly, and the only way out was a
forced power-off. Two different causes were found:

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

Resolution of the 2026-10-19 hang: `modules/hardware/nvidia.nix` sets
`hardware.nvidia.moduleParams.nvidia.NVreg_DynamicPowerManagement = 0`. With the MUX set to the
discrete GPU, the GPU drives the panel whenever the screen is on, so runtime D3 only applied
while the screen was off and saved nothing that matters next to sleep and hibernation.

### Lock screen carried through hibernation

From 2026-10-21 to 2026-10-23, every sleep started after a resume from hibernation, while the
session was still locked, hung: the journal stops at `PM: suspend entry (s2idle)`, the keyboard
stays fully lit instead of its sleep pattern (two ZQSD blinks, then waves), and the next key press
makes the firmware reset or power off the machine. The firmware register read at boot recorded
`software wrote 0xE to reset control register 0xCF9` and `ACPI power state transition occurred`
after the resets, nothing after the power-offs.

Cause: the lock screen process (`kscreenlocker_greet`) that was on screen when the machine
hibernated. Plasma locks the session before hibernation, so after the resume the same greeter
process, restored from the image, is still displayed. While it is, the next sleep hangs in the
device suspend phase. Logging in closes it; a later sleep then starts a new greeter and works.
What inside the greeter, KWin or the NVIDIA driver makes the device suspend hang is not known.

Resolution: `modules/desktop/plasma.nix` adds `restart-lock-screen-after-hibernation`, a oneshot
service ordered after `systemd-hibernate.service` and `systemd-suspend-then-hibernate.service`. It
kills `kscreenlocker_greet`; the screen locker starts a new greeter at once and the session stays
locked.

Findings that narrowed the cause:

| Test | Result | Conclusion |
| --- | --- | --- |
| Sleep without login after a cold boot, in every variant | Works | The hibernation resume is required |
| Login, then sleep two seconds later | Works | Logging in protects; elapsed time does not matter |
| Hardware state before and after unlocking: 1100 device power states, LEDs, backlight, outputs, ASUS attributes, GPU power, USB | Identical, only `LockedHint` changes | Unlocking changes software state only |
| Sleep requested by `systemctl` while locked | Hangs | The Plasma sleep request path is not the cause |
| `pm_test` at `devices`, and with `pm_async = 0` | Power-off or hang | The hang is in the device suspend phase, not a race between devices |
| Greeter killed while locked, then sleep, twice | Works | The greeter carried through hibernation is the cause |

Hypotheses ruled out on the way:

- the `mt7921e` restore error ([incident](mt7921e-hibernation-restore.md));
- the ACP and HD Audio race ([incident](amd-acp-hda-resume-race.md));
- keyboard, mouse and RTC wakeups ([incident](hibernation-wakeup-hang.md));
- NVIDIA bug 5156763, fixed in 595.104.02 (`InHibernate` cleared in `dynamic-power.c`);
- the GCOFF path: `S0ixPowerManagementVideoMemoryThreshold = 0` did not help;
- the kernel suspend callback of the NVIDIA driver, which only counts when the GPU is already
  suspended;
- asusd, whose keyboard sleep task never runs.

The driver reads its options only when it is loaded: the RTD3 change takes effect after
`nixos-rebuild boot` and a real reboot, never after a resume from hibernation.

## How to verify the fix

1. Confirm the service is installed.

   ```bash
   systemctl cat restart-lock-screen-after-hibernation
   ```

2. Hibernate, power on, and do not log in. After the resume, the lock screen flickers once while
   it is replaced.

   ```bash
   systemctl hibernate
   ```

3. From the lock screen, choose Sleep, wait one minute, then press a key. The machine must wake
   to the lock screen, and the keyboard must show its sleep pattern while asleep.

4. Confirm the service ran.

   ```bash
   journalctl -b -u restart-lock-screen-after-hibernation
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
