# Hibernation hang: CS35L41 firmware reload deadlock

## Overview

From 2026-11-02, every hibernation wrote its image and then left the laptop on, screen black and
fans running, until a forced power-off. The next boot resumed the session, so the image was
complete. The ten hibernations of 2026-10-23 and 2026-10-24 had powered off normally, with the same
kernel and NVIDIA driver as the first failure.

Affected configuration:

| Component | Version |
| --- | --- |
| Kernel | `linuxPackages_zen` 7.2.9, then 7.2.14 with the hibernation authentication patches |
| Speaker amplifiers | Two Cirrus Logic CS35L41 on I2C (`CSC3551`), driver `snd_hda_scodec_cs35l41`, firmware loaded at boot (`spk-prot`) |
| Root and store file system | Btrfs on LUKS |
| Hibernation mode | `platform`; `shutdown` hangs as well |

Cause: a deadlock between the CS35L41 driver and the hibernation sequence.

1. Hibernation freezes tasks and freezable workqueues, takes the snapshot, then thaws the devices
   to write the image. Tasks and freezable workqueues stay frozen until the machine powers off.
2. The driver uses one function, `cs35l41_system_resume`, for resume, thaw and restore. At thaw it
   schedules the firmware reload on `system_wq`, which is not frozen. The reload takes `fw_mutex`
   and calls `request_firmware`.
3. Btrfs completes its reads on the `btrfs-endio` and `btrfs-endio-meta` workqueues, which are
   freezable. When the firmware files or their directory entries are no longer cached, the reload
   waits for a read that never completes, and keeps `fw_mutex`.
4. Before powering off, the kernel calls the `prepare` callback of every device.
   `cs35l41_system_suspend_prep` waits for `fw_mutex` forever, so the kernel never reaches the
   power-off.

The reload has been scheduled at thaw since the driver gained system suspend support (commit
`88672826e2a4`, "ALSA: hda: cs35l41: Support System Suspend"). The hang depends on the page cache:
in October the reload after a resume completed while tasks were still frozen, so its files were
cached; from November it completed only after the tasks restarted, so it had read the disk. What
changed the cache state between the two periods is not known. Mainline v7.4-rc1 still schedules the
reload on `system_wq`.

Resolution: `custom.audio.deferCs35l41FirmwareReload` applies
`kernel/patches/cs35l41-freezable-fw-load/`, which queues the reload on `system_freezable_wq`.
After thaw the work stays pending until the machine powers off; on a real resume it runs once the
tasks restart, about one second later, when the files can be read. The patch is meant for upstream
and is independent of the hibernation authentication series.

Findings that narrowed the cause:

| Test | Result | Conclusion |
| --- | --- | --- |
| Console messages on a text VT during hibernation | Screen black from the start | `nvidia-sleep.sh` switches to VT 63 and suspends the GPU that drives the panel before the kernel starts: this method shows nothing on this machine |
| Wakeup of the GPU root port (`GPP0`) disarmed | Hang | Not a wakeup source on that port |
| External USB SSD unplugged | Hang | Not that device |
| OpenRGB, the lighting daemons and `i2c_dev` stopped | Hang | Not the lighting stack |
| `pm_trace`, RTC read in the firmware setup | Last trace: end of a device resume at thaw | No device had started its power-off callback: the hang is between the image write and the first `poweroff` |
| `HibernateMode=shutdown` | Hang | The shutdown path also blocks; the NVIDIA shutdown path is a known separate problem (`open-gpu-kernel-modules` issue 1486) |
| SysRq `w`, `l`, `c` after the hang, read back through `efi_pstore` | `systemd-sleep` in `cs35l41_system_suspend_prep`, two workers in `cs35l41_fw_load_work` waiting on Btrfs reads | Deadlock on `fw_mutex` |
| Firmware load controls of both amplifiers set to `off` before hibernation | Powered off by itself | The reload at thaw is the cause |
| Patched kernel, three hibernations on mains and on battery, charger and input devices toggled during the power cut | Powered off every time, firmware reloaded after the tasks restarted | Fixed |

The firmware load controls cannot be changed while a stream plays: the audio monitor of the lighting
daemon keeps the speaker output running, so the driver answers `Device or resource busy` until that
daemon is stopped.

## How to verify the fix

1. Confirm that the running kernel carries the patch. The command must print `1`.

   ```bash
   xz -dc $(find -L /run/current-system/kernel-modules/lib/modules -name 'snd-hda-scodec-cs35l41.ko.xz') | grep -a -c system_freezable_wq
   ```

2. Hibernate, without touching the machine, and wait for it to power off.

   ```bash
   systemctl hibernate
   ```

3. After the resume, confirm that both amplifiers reloaded their firmware after the tasks
   restarted.

   ```bash
   journalctl -b 0 -k | grep -E 'Restarting tasks: Done|Firmware Loaded' | tail -3
   ```

## How to locate a hang after the image is written

Kernel messages written after the snapshot never reach the journal, and the panel is already off.
Two methods still work on this machine. Neither changes the configuration; both reset at reboot.

To find the last device callback with `pm_trace`:

1. Enable the trace.

   ```bash
   echo 1 | sudo tee /sys/power/pm_trace /sys/power/pm_debug_messages
   ```

2. Hibernate, wait 2 minutes after the screen goes black, force the power-off, power on and press
   F2 at the ASUS logo. Photograph the date and time of the firmware setup at once, then leave
   without saving. The value is valid for about 3 minutes after the hang.
3. Decode the date, with integer divisions. With `yy` the two-digit year, `mon0` the month
   counted from 0, `mday` the day, and `hour` and `min` the time:
   `n = yy + 100 * (mon0 + 12 * (mday - 1 + 28 * (hour + 24 * (min / 3))))`. The device hash is
   `n / 16 / 997`, the file and line hash is `n / 16 % 997`. Match them with `hash_string` of
   `drivers/base/power/trace.c`: seed 7919 and modulus 1009 for device names, the line number as
   seed and modulus 997 for `drivers/base/power/main.c`.
4. After the resume, disable the trace. chrony steps the clock back on its own.

   ```bash
   echo 0 | sudo tee /sys/power/pm_trace /sys/power/pm_debug_messages
   ```

To capture the stacks of the blocked tasks with SysRq and `efi_pstore`, when the hang happens
before the USB devices power off:

1. Allow the dump and crash keys until reboot.

   ```bash
   sudo sysctl kernel.sysrq=24
   ```

2. Hibernate and wait 2 minutes. On a keyboard with a Print Screen key, wake it with Alt, then
   hold Alt and Print Screen and press `w`, `l` and `c`, a few seconds apart. SysRq reads key
   positions: on an AZERTY layout, `w` is the Z key.
3. Wait 10 seconds, force the power-off and let the session resume. The panic records are EFI
   variables, visible at once:

   ```bash
   ls /sys/firmware/efi/efivars/ | grep dump-type0
   ```

   Each variable holds a 4-byte attribute header followed by a raw deflate stream (`-15` window
   bits in Python `zlib`); `Part1` is the end of the log. Read them with `cat`, which works where
   `cp` fails on efivarfs. `systemd-pstore` archives and deletes them at the next real boot.

## Reference

| Source | Content |
| --- | --- |
| [Linux kernel, debugging hibernation and suspend](https://docs.kernel.org/power/basic-pm-debugging.html) | Hibernation phases, `pm_trace` |
| [Linux kernel, s2ram debugging](https://docs.kernel.org/power/s2ram.html) | How `pm_trace` stores its hash in the RTC |
| [Linux kernel, SysRq](https://docs.kernel.org/admin-guide/sysrq.html) | `kernel.sysrq` bit mask, `w`, `l` and `c` keys |
| [Linux kernel, pstore](https://docs.kernel.org/admin-guide/ramoops.html) | Persistent storage of kernel logs on panic |
| [Linux kernel, workqueue](https://docs.kernel.org/core-api/workqueue.html) | `WQ_FREEZABLE` and `system_freezable_wq` |
| [NVIDIA open-gpu-kernel-modules issue 1486](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/1486) | Separate NVIDIA hang in the `shutdown` hibernation mode since driver 595 |
| `sound/hda/codecs/side-codecs/cs35l41_hda.c` | `cs35l41_system_resume`, `cs35l41_system_suspend_prep`, `cs35l41_fw_load_work` |
| `fs/btrfs/disk-io.c` | Freezable Btrfs workqueues |
