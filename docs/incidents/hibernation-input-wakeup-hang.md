# Hibernation hang on keyboard or mouse activity

## Overview

After the fix of [hibernation-power-off](hibernation-power-off.md), hibernation still failed
twice out of fourteen, on 2026-10-21 and 2026-10-22: the image was written, the screen went
black, and the laptop stayed on until a forced power-off. The next boot resumed the session, so
only the final power cut failed. On 2026-10-21 the kernel ran with `hung_task_panic`,
`softlockup_panic` and `hardlockup_panic`, and none fired in four minutes.

Affected configuration:

| Component | Version |
| --- | --- |
| Kernel | `linuxPackages_zen` 7.2.9 |
| Firmware | ASUS BIOS G713PI.336 |
| Wake sources | Internal keyboard (USB `N-KEY Device`) and USB mouse with `power/wakeup` enabled; their xHCI controllers enabled for S4 in `/proc/acpi/wakeup` |

Cause: a keyboard or mouse event that reaches the platform during the last step of hibernation.
After writing the image, the kernel powers the devices down with their wakeup armed, takes the
secondary CPUs offline, disables interrupts, checks a last time for a pending wakeup event, then
asks the firmware for S4. An event caught before that check makes the kernel roll back and return
to the session:

```text
Wakeup pending. Abort CPU freeze
PM: hibernation: Wakeup event detected during hibernation, rolling back.
```

An event that arrives after it leaves a wake request pending when S4 is entered. The platform then
does not power off, and the kernel, which never expects to return from S4, waits forever with
interrupts disabled (`acpi_hw_legacy_sleep` in `drivers/acpi/acpica/hwsleep.c`, then
`hibernation_platform_enter` in `kernel/power/hibernate.c`). No lockup detector can report a CPU
spinning with interrupts off on the last online CPU.

Both failures followed a `systemctl hibernate` typed in a terminal, with the hands still on the
keyboard; in both, the journal shows a key still held when the session froze (`Key repeat
discarded`).

Resolution: `modules/hardware/power.nix` installs a `system-sleep` hook, enabled by
`custom.power.disarmInputWakeupForHibernation`. Before hibernation, including the hibernation
phase of "sleep, then hibernate", it sets `power/wakeup` to `disabled` on every USB device with a
HID interface whose wakeup was enabled, and records them in `/run/hibernate-input-wakeup`. After
the transition, it enables them again. Sleep keeps waking on a key press; hibernation only wakes
with the power button, as it already did from a powered-off state.

Findings that narrowed the cause, with the mouse moved and a key pressed every second from the
`systemctl hibernate` command until power-off:

| Test | Result | Conclusion |
| --- | --- | --- |
| Firmware methods run at power-off: `_PTS(4)` and the ACP and HD Audio `_PS3` of `CPMACPV7` | Every wait is bounded | The firmware code reached by ACPI cannot loop forever |
| Kernel log of failed and successful hibernations | Identical up to the snapshot | Nothing before the image write distinguishes them |
| Activity during hibernation, defaults | One power-off failure out of one | Activity reproduces the failure |
| Activity, chrony stopped | One failure, two rollbacks with `Wakeup pending. Abort CPU freeze` | Activity reaches the power-down; the RTC readings of chrony are not the cause |
| Activity, `power/wakeup` disabled on the keyboard and the mouse | Three clean power-offs | Input wakeup during power-down is the cause |

A related effect, not a failure: chrony reads the RTC every minute through RTC update interrupts.
On AMD firmware from 2021 on, `rtc-cmos` routes them through the ACPI RTC event and reports each
as a wakeup event. When one lands while the tasks are being frozen, the hibernation is cancelled
with `Freezing remaining freezable tasks aborted` and `Device or resource busy`, and the session
comes back at once.

## How to verify the fix

1. Confirm the hook is installed.

   ```bash
   ls -l /etc/systemd/system-sleep/hibernate-input-wakeup
   ```

2. Hibernate, then move the mouse and press keys until the machine is off. It must power off.

   ```bash
   systemctl hibernate
   ```

3. After the resume, confirm the keyboard and the mouse can wake the machine again. Both lines must
   read `enabled`.

   ```bash
   cat /sys/bus/usb/devices/7-1/power/wakeup /sys/bus/usb/devices/5-1/power/wakeup
   ```

   The bus paths `7-1` and `5-1` belong to this machine and its usual mouse port.

## Reference

| Source | Content |
| --- | --- |
| [Linux kernel, device power management](https://docs.kernel.org/driver-api/pm/devices.html) | Wakeup sources, `power/wakeup` |
| [Linux kernel, debugging hibernation and suspend](https://docs.kernel.org/power/basic-pm-debugging.html) | Hibernation phases |
| [systemd-sleep(8)](https://www.freedesktop.org/software/systemd/man/latest/systemd-sleep.html) | `system-sleep` hooks and `SYSTEMD_SLEEP_ACTION` |
| [ACPI specification, sleeping states](https://uefi.org/specs/ACPI/6.5/16_Waking_and_Sleeping.html) | Wake events, `SLP_EN`, `WAK_STS` |
