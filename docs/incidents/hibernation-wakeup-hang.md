# Hibernation hang on late wakeup events

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
| Input wake sources | Internal keyboard (USB `N-KEY Device`) and USB mouse with `power/wakeup` enabled; their xHCI controllers enabled for S4 in `/proc/acpi/wakeup` |
| RTC | `rtc-cmos` with `use_acpi_alarm` set, chosen by the kernel for AMD firmware from 2021 on |
| chrony | `rtcfile` and `rtcautotrim`, the NixOS default of `services.chrony.enableRTCTrimming` |

Cause: a wakeup event that reaches the platform during the last step of hibernation. After
writing the image, the kernel powers the devices down with their wakeup armed, takes the secondary
CPUs offline, disables interrupts, checks a last time for a pending wakeup event, then asks the
firmware for S4. An event caught before that check makes the kernel roll back and return to the
session:

```text
Wakeup pending. Abort CPU freeze
PM: hibernation: Wakeup event detected during hibernation, rolling back.
```

An event that arrives after it leaves a wake request pending when S4 is entered. The platform then
does not power off, and the kernel, which never expects to return from S4, waits forever with
interrupts disabled (`acpi_hw_legacy_sleep` in `drivers/acpi/acpica/hwsleep.c`, then
`hibernation_platform_enter` in `kernel/power/hibernate.c`). No lockup detector can report a CPU
spinning with interrupts off on the last online CPU. The window cannot be closed from the
configuration; only the sources that fire in it can be removed.

Two sources fire without reason during hibernation:

- **Keyboard and mouse.** Both failures followed a `systemctl hibernate` typed in a terminal, with
  the hands still on the keyboard; in both, the journal shows a key still held when the session
  froze (`Key repeat discarded`). Moving the mouse during hibernation reproduced the hang.
- **RTC readings of chrony.** With `rtcfile` and `rtcautotrim`, chrony enables the RTC update
  interrupt every minute to measure the RTC drift. With `use_acpi_alarm`, the kernel emulates that
  interrupt with an RTC alarm, which arrives through the ACPI RTC event, and `rtc_handler` in
  `drivers/rtc/rtc-cmos.c` reports each one with `pm_wakeup_hard_event`. When chrony is frozen in
  the middle of a measurement, the alarm keeps firing every second through the whole hibernation.
  Holding the update interrupt on made every hibernation abort while the tasks froze:

  ```text
  Freezing remaining freezable tasks aborted after 0.000 seconds (1 tasks refusing to freeze, wq_busy=0):
  systemd-sleep: Failed to put system to sleep. System resumed again: Device or resource busy
  ```

  A hang caused by the RTC was not observed directly: one hang occurred with the input wakeup
  disarmed, no input, and chrony as the only active source. It is attributed to the RTC because it
  uses the same wakeup path.

Resolution:

| Source | Change |
| --- | --- |
| Keyboard and mouse | `modules/hardware/power.nix` installs a `system-sleep` hook, enabled by `custom.power.disarmInputWakeupForHibernation`. Before hibernation, including the hibernation phase of "sleep, then hibernate", it sets `power/wakeup` to `disabled` on every USB device with a HID interface whose wakeup was enabled, and records them in `/run/hibernate-input-wakeup`; after the transition, it enables them again |
| RTC | `modules/network/time.nix` sets `services.chrony.enableRTCTrimming = false` and adds `rtcsync`: the kernel copies the system time to the RTC every 11 minutes with a plain write, without interrupts or alarms |

Sleep keeps waking on a key press; hibernation wakes only with the power button, as it already did
from a powered-off state. chrony no longer corrects the RTC drift between boots; it steps the clock
once the network servers answer.

A remaining source is the power supply: `ADP0` and the USB-C `ucsi` source are wakeup sources too,
so plugging or unplugging the charger during the power cut can still hang it.

Findings that narrowed the cause:

| Test | Result | Conclusion |
| --- | --- | --- |
| Firmware methods run at power-off: `_PTS(4)` and the ACP and HD Audio `_PS3` of `CPMACPV7` | Every wait is bounded | The firmware code reached by ACPI cannot loop forever |
| Kernel log of failed and successful hibernations | Identical up to the snapshot | Nothing before the image write distinguishes them |
| Mouse moved and a key pressed every second, defaults | One hang out of one | Input activity reproduces the hang |
| Same activity, chrony stopped | One hang, two rollbacks with `Wakeup pending. Abort CPU freeze` | Input activity alone causes the hang |
| Same activity, chrony stopped, input wakeup disabled | Three clean power-offs | Without input and RTC sources, the power cut succeeds |
| No input, input wakeup disarmed by the hook, chrony running | One hang | A second source remains |
| No input, chrony stopped, RTC update interrupt held on | Three aborts while freezing | RTC interrupts are wakeup events during hibernation |

## How to verify the fix

1. Confirm the hook is installed and that chrony no longer measures the RTC. The second command
   must print `rtcsync` and no `rtcfile`.

   ```bash
   ls -l /etc/systemd/system-sleep/hibernate-input-wakeup
   ```

   ```bash
   grep -hE 'rtc' $(systemctl cat chronyd | grep -o '/nix/store/[^ ]*chrony.conf')
   ```

2. Confirm the RTC wakeup source stays idle. The command prints one count per RTC wakeup source;
   read them twice, two minutes apart; they must not change.

   ```bash
   grep -l '^PNP0B00:00$' /sys/class/wakeup/*/name | xargs -n1 dirname | xargs -I{} cat {}/event_count
   ```

3. Hibernate, then move the mouse and press keys until the machine is off. It must power off.

   ```bash
   systemctl hibernate
   ```

4. After the resume, confirm the keyboard and the mouse can wake the machine again. Both lines must
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
| [chrony.conf(5)](https://chrony-project.org/doc/4.9/chrony.conf.html) | `rtcfile`, `rtcautotrim`, `rtcsync` |
| [NixOS options search](https://search.nixos.org/options?channel=unstable&query=services.chrony.enableRTCTrimming) | `services.chrony.enableRTCTrimming` |
