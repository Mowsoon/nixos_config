# No sound after sleep: ACP and HD Audio resume race

## Overview

From the installation on 2026-10-17, the speakers and the headphone jack went silent after every
sleep. PipeWire kept the Ryzen output and showed the streams as active, but nothing played until
the next hibernation or reboot. Every resume logged:

```text
snd_hda_intel 0000:09:00.6: CORB reset timeout#2, CORBRP = 65535
cs35l41-hda i2c-CSC3551:00-cs35l41-hda.0: Enable(1) failed: -110
```

Of 30 sleeps recorded until 2026-10-22, every one that lasted more than a few seconds broke the
audio; the ones without errors were aborted sleeps of 0 to 2 seconds. None of 20 resumes from
hibernation broke it.

Affected configuration:

| Component | Version |
| --- | --- |
| Kernel | `linuxPackages_zen` 7.2.9 |
| Audio block | AMD HD Audio controller `1022:15e3` at `09:00.6`, audio coprocessor (ACP) `1022:15e2` revision `0x62` at `09:00.5`, bound to `snd_pci_acp6x` |
| Codec and amplifiers | Realtek ALC294, two Cirrus CS35L41 on I2C |
| Firmware | ASUS BIOS G713PI.336 |

Cause: the HD Audio controller and the ACP are two PCI functions of one audio block, which the
firmware powers off in sleep. On resume, the ACPI `_PS0` method of each function marks the
function as present, then calls a shared method that powers the block up only when exactly one
function is marked. The mark is set outside the lock of the shared method. When the kernel resumes
both functions in parallel, which is its default, both are marked before either reaches the check;
each assumes the other powered the block up, and nobody does. The controller stays unpowered and
all its registers read as ones, which the driver reports as the `CORBRP = 65535` timeout. The
amplifiers time out in turn, because they take their audio clock from the codec, which the dead
controller no longer drives.

Linux 7.1 made the race reachable: commit `df4148a5a3cf` ("ASoC: Add DMIC support for the AMD RPL
platform") bound the revision `0x62` ACP of Dragon Range and Fire Range processors to
`snd_pci_acp6x`, so the ACP now resumes alongside the HD Audio controller. A kernel patch that
resumes the two functions one after the other was posted on 2026-10-16 and is not merged yet. An
AMD maintainer asked whether a firmware update fixes it first; a similar report was fixed that way.
The patch describes the AMD `CPMACPV4` ACPI table, while this firmware ships `CPMACPV7`; the table
was not inspected, the test below confirms the same behaviour.

Resolution: `modules/hardware/audio.nix` declares a udev rule, enabled by
`custom.audio.serializeAmdAcpResume`, that sets `power/async` to `disabled` on both functions when
they are detected. The kernel then suspends and resumes them synchronously, as the upstream patch
does, without rebuilding the kernel.

Findings that narrowed the cause:

| Test | Result | Conclusion |
| --- | --- | --- |
| Stream status in `/proc/asound/card1/pcm0p/sub0/status` after resume | `hw_ptr` a whole number of buffers, `appl_ptr` stuck | The controller never moves the stream; ALSA extrapolates the position from elapsed time |
| Headphones after resume | Silent | Not an amplifier fault |
| Driver unbind and bind of `09:00.6` | `chipset global capabilities = 0xffff`, `no codecs initialized` | The controller is unpowered; a driver initialization cannot reach it |
| ACP forced awake with `power/control=on`, then driver rebind | No change | Consistent with the race: the controller is already marked present, so the shared method skips the power up |
| `power/async` disabled on both functions, then two sleeps | Sound kept, no error | Parallel resume is the cause |
| Hibernation | Sound back | Firmware powers the block at boot |

The ACP driver itself serves no sound card on this model, as described in the Audio section of
the hardware documentation.

## How to verify the fix

1. Confirm the rule applied to both functions after a reboot. Both lines must read `disabled`.

   ```bash
   cat /sys/bus/pci/devices/0000:09:00.5/power/async /sys/bus/pci/devices/0000:09:00.6/power/async
   ```

2. Play a sound, sleep for at least 30 seconds, wake the machine, and play it again.

   ```bash
   systemctl suspend
   ```

3. Confirm the resume logged neither error. The command must print nothing.

   ```bash
   journalctl -b 0 | grep -E 'CORB reset timeout|Enable\(1\) failed'
   ```

## How to restore the sound without the fix

The block only powers up again from firmware: hibernate, or reboot. Rebinding the driver does not
help.

## How to check whether the fix is still needed

Run this after a kernel or firmware update.

1. Look for the message of the upstream quirk in the kernel log.

   ```bash
   journalctl -b 0 -k | grep 'async suspend disabled to avoid ACP/HD Audio power up race'
   ```

2. If it is present, the kernel serializes the two functions itself: remove
   `serializeAmdAcpResume` from `hosts/hephaestus/hardware.nix`, then the option and its rule
   from `modules/hardware/audio.nix`.
3. After a firmware update, test without the rule: disable the option, reboot, and sleep twice.
   Keep the rule removed only if both resumes keep the sound.

## Reference

| Source | Content |
| --- | --- |
| [Upstream patch](https://lore.kernel.org/all/20261016135042.44914-1-diogogsousa@gmail.com/T/) | "PCI: Disable async suspend for AMD rev 0x62 ACP and HD Audio", ACPI analysis and review |
| [CachyOS issue 950](https://github.com/CachyOS/linux-cachyos/issues/950) | Same failure on other Dragon Range and Fire Range laptops, `pm_async` workaround |
| [AMD issue 5529](https://gitlab.freedesktop.org/drm/amd/-/work_items/5529) | Similar report fixed by a firmware update |
| [Linux kernel, device power management](https://docs.kernel.org/driver-api/pm/devices.html) | Asynchronous suspend and resume, `power/async` |
| [sysfs-devices-power ABI](https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-devices-power) | `/sys/devices/.../power/async` |
