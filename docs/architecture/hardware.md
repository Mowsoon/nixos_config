# Hardware

## Overview

The workstation is an ASUS ROG Strix G17 G713PI laptop: AMD Ryzen 9 7845HX, NVIDIA GeForce RTX 4070
Laptop GPU, AMD Radeon 610M integrated GPU, two NVMe disks. No `nixos-hardware` profile exists for
this model; `hosts/hephaestus/hardware.nix` composes the generic AMD CPU, NVIDIA and laptop
profiles with the modules under `modules/hardware/`.

### Kernel and CPU

The kernel is the zen variant (`linuxPackages_zen`), tuned for desktop latency. The CPU runs the
`amd-pstate` driver in active mode, and power-profiles-daemon switches between the power saver,
balanced and performance profiles. `kvm-amd` is loaded for virtual machines.

power-profiles-daemon pairs the Performance platform profile with the `performance` governor and
the `performance` energy performance preference (EPP), which keeps the cores in boost at idle. A
runtime test on 2026-10-19 kept the Performance platform profile with the `powersave` governor
and the `balance_performance` EPP: the machine idles at about 25 W and 59 °C instead of 47 W and
91 °C, with no throughput loss under an all-core load, where both settings hold the 95 °C
thermal target at the same clock. Making this pairing permanent is pending a Nix change; until
then the Performance profile runs with the `performance` EPP.

### Graphics

The firmware MUX switch decides which GPU drives the internal panel, and it is set to the discrete
GPU only. NixOS therefore runs the NVIDIA GPU alone: no PRIME offload, no `supergfxd`, no bus
identifiers to declare.

The driver uses the NVIDIA open kernel modules from the `stable` branch, with kernel mode setting
for Wayland and Dynamic Boost, which shifts power between CPU and GPU under load. Its power
management settings are the result of two incidents:

- `powerManagement.enable` saves video memory before sleep and hibernation and restores it on
  resume, through the `nvidia-suspend`, `nvidia-hibernate` and `nvidia-resume` systemd units.
- `kernelSuspendNotifier = false` keeps those systemd units. With the kernel suspend notifier path
  of driver 595, the machine never powered off after writing a hibernation image
  ([incident](../incidents/hibernation-power-off.md)).
- The nixpkgs module hooks those units to plain sleep and hibernation only. The NVIDIA module adds
  the `nvidia-suspend-then-hibernate` unit and installs the driver's `system-sleep` hook, which
  switches the driver from sleep to hibernation when the hibernation delay expires. Without them,
  the driver refused "sleep, then hibernate"
  ([incident](../incidents/suspend-then-hibernate-nvidia.md)).
- `NVreg_EnableS0ixPowerManagement = 1` makes the driver handle `s2idle` as a low-power idle
  state instead of a full power cut. Without it, the desktop froze after resuming from sleep
  ([incident](../incidents/suspend-resume-freeze.md)).

The driver reads its options only when it is loaded: a change to them takes effect after
`nixos-rebuild boot` and a real reboot, never after a resume from hibernation.

Video decoding goes through `nvidia-vaapi-driver`, which translates VA-API, the decoding interface
Firefox and most players use, to NVDEC, the decoder of the GPU. It uses its `direct` backend,
because the EGL one no longer works since driver 525. That backend calls an internal interface of
the kernel driver that NVIDIA does not keep stable, so a driver update can break it; Firefox then
falls back to software decoding. Firefox blocklists hardware decoding on NVIDIA, which the NVIDIA
module lifts with `media.hardware-video-decoding.force-enabled`. The RDD sandbox, the process that
decodes web video, stays enabled.

### Sleep and power

The firmware exposes Modern Standby only: `s2idle` is the single sleep state, and its consumption
depends on every driver reaching its low-power state. Two settings bound the battery drain:

- a sleep started from Plasma as "sleep, then hibernate" turns into hibernation after 2 h
  (`HibernateDelaySec`);
- UPower hibernates the machine when the battery reaches its critical level.

Inside a Plasma session, PowerDevil decides what the lid switch and the power key do; these
choices live in the Plasma energy settings, not in logind. Only the "Standby, then hibernate"
sleep mode calls `SuspendThenHibernate` and so honours `HibernateDelaySec`; `systemctl suspend` and
the plain "Standby" mode never hibernate. Hibernation writes the image to the
swapfile described in [Storage](storage.md) and resumes through the initrd described in
[Boot chain](boot-chain.md).

### ASUS platform

asusd drives the fan curves, the power profiles of the firmware, the keyboard backlight and the
battery charge limit; ROG Control Center is its graphical front end. Fan curves and profiles
changed in ROG Control Center are learned state stored in `/etc/asusd`, which is persisted. They
are tuned with the measured procedure in [Fan curve tuning](../operations/fan-curve-tuning.md). The
thermal interface is replaced with
[Thermal interface replacement](../operations/thermal-interface-replacement.md).

asusd also acts on the platform profile and the EPP, alongside power-profiles-daemon. Its learned
configuration, `/etc/asusd/asusd.ron`, switches the platform profile to Performance when the
charger is plugged in and to Quiet when it is unplugged, and writes the EPP linked to the profile
on every profile change. A profile chosen through power-profiles-daemon or Plasma therefore
changes at every charger event, and a runtime EPP is overwritten at the next profile change.

The battery charge limit is declared instead: a oneshot service, `asus-charge-limit`, applies
`custom.asus.chargeLimit` through `asusctl` at every boot, after asusd starts. The limit is 80 %,
which slows battery wear on a laptop that stays plugged in.

### Audio

PipeWire is the audio server, with its ALSA, PulseAudio and JACK compatibility layers and
WirePlumber as session manager. rtkit grants it real-time scheduling. Device access goes through
the logind seat of the session. The effects processor, EasyEffects, runs as a user service
declared in the user environment.

### Peripherals

BlueZ runs with its experimental features, which report the battery level of Bluetooth headsets
to Plasma. Pairing keys are persisted. The udev rules for Logitech wireless receivers let Solaar
configure the devices without root. input-remapper is available for remapping external keyboards;
its presets live in the persistent home.

### Disk health

smartd monitors every detected disk and sends a desktop notification through the system bus when
an attribute crosses its failure threshold.

## How to check the graphics driver state

1. Check that the discrete GPU is active and see its power state.

   ```bash
   nvidia-smi
   ```

2. Check the power management options the driver was loaded with.

   ```bash
   grep -E 'EnableS0ixPowerManagement|UseKernelSuspendNotifiers|PreserveVideoMemoryAllocations' /proc/driver/nvidia/params
   ```

   ```text
   PreserveVideoMemoryAllocations: 1
   EnableS0ixPowerManagement: 1
   UseKernelSuspendNotifiers: 0
   ```

## How to test a driver or kernel option

1. Change the option in the module, then install the generation as the next boot entry.

   ```bash
   sudo nixos-rebuild boot --flake ~/.config/nixos#hephaestus
   ```

2. Reboot with `systemctl reboot`. A resume from hibernation restores the previous kernel and
   driver options, and does not test the change.
3. Confirm the running system is the new generation. Both paths are identical.

   ```bash
   readlink /run/booted-system /nix/var/nix/profiles/system
   ```

## How to change the battery charge limit

1. Set `custom.asus.chargeLimit` in `hosts/hephaestus/hardware.nix` to a value between 20 and 100.
2. Apply the configuration. The service runs again on activation.
3. Read the limit applied by the firmware.

   ```bash
   cat /sys/class/power_supply/BAT*/charge_control_end_threshold
   ```

## How to check the sleep states

1. List the sleep states the firmware offers. The selected one is in brackets.

   ```bash
   cat /sys/power/mem_sleep
   ```

   ```text
   [s2idle]
   ```

2. Check the hibernation delay and the sleep modes systemd uses.

   ```bash
   systemd-analyze cat-config systemd/sleep.conf
   ```

## How to test sleep then hibernate without waiting

1. Shorten the delay until the next reboot with a runtime drop-in, which lives in memory.

   ```bash
   sudo mkdir -p /run/systemd/sleep.conf.d
   printf '[Sleep]\nHibernateDelaySec=2min\n' | sudo tee /run/systemd/sleep.conf.d/test.conf
   ```

2. Close the lid for more than 2 minutes, then open it. The machine must go through firmware and
   LUKS unlock before the session comes back: it resumed from hibernation, not from sleep.
3. Check the path logind took.

   ```bash
   journalctl -b -u systemd-suspend-then-hibernate.service --no-pager
   ```

4. Remove the drop-in, or reboot.

   ```bash
   sudo rm /run/systemd/sleep.conf.d/test.conf
   ```

## How to read the health of a disk

1. Print the SMART data of the Linux disk.

   ```bash
   sudo smartctl -a /dev/nvme0
   ```

   The `Percentage Used` and `Media and Data Integrity Errors` attributes show the wear and the
   uncorrected errors. The device name of each disk is listed by `lsblk`.

## Reference

### Hardware profile

| Component | Value |
| --- | --- |
| Model | ASUS ROG Strix G17 G713PI |
| CPU | AMD Ryzen 9 7845HX, `amd-pstate` active |
| Discrete GPU | NVIDIA GeForce RTX 4070 Laptop GPU (AD106M) |
| Integrated GPU | AMD Radeon 610M, unused behind the MUX |
| Linux disk | Samsung 990 PRO, NVMe |
| Windows disk | Western Digital SN560, NVMe |
| Sleep states | `s2idle` only, hibernation to disk |

### Kernel and firmware

| Setting | Value |
| --- | --- |
| `boot.kernelPackages` | `linuxPackages_zen` |
| `boot.kernelModules` | `kvm-amd` |
| `boot.initrd.availableKernelModules` | `nvme`, `xhci_pci`, `usbhid` |
| `hardware.enableRedistributableFirmware` | `true` |
| `nixos-hardware` profiles | `common-cpu-amd-pstate`, `common-gpu-nvidia-nonprime`, `common-pc-laptop` |

### NVIDIA driver

| Setting | Value |
| --- | --- |
| `hardware.nvidia.open` | `true` |
| `hardware.nvidia.package` | `nvidiaPackages.stable` of the running kernel |
| `hardware.nvidia.modesetting.enable` | `true` |
| `hardware.nvidia.powerManagement.enable` | `true` |
| `hardware.nvidia.powerManagement.kernelSuspendNotifier` | `false` |
| Suspend-then-hibernate unit and hook | `nvidia-suspend-then-hibernate`, `/etc/systemd/system-sleep/nvidia` |
| `hardware.nvidia.dynamicBoost.enable` | `true` |
| `NVreg_EnableS0ixPowerManagement` | `1` |
| `hardware.graphics.enable32Bit` | `true` |
| `hardware.graphics.extraPackages` | `nvidia-vaapi-driver` |
| `LIBVA_DRIVER_NAME` | `nvidia` |
| `NVD_BACKEND` | `direct` |
| Firefox `media.hardware-video-decoding.force-enabled` | `true` |

### Plasma energy settings

Set by hand in System Settings, Power Management, in the AC, Battery and Low Battery profiles;
stored in `~/.config/powerdevilrc`.

| Setting | Value | Profiles |
| --- | --- | --- |
| When laptop lid closed | Sleep | All |
| When power button pressed | Show logout screen | All |
| When sleeping, enter | Standby, then hibernate | All |
| At critical level | Hibernate | Low Battery |

### Power settings

| Setting | Value |
| --- | --- |
| `systemd.sleep.settings.Sleep.HibernateDelaySec` | `2h` |
| `services.upower.criticalPowerAction` | `Hibernate` |
| `services.power-profiles-daemon.enable` | `true` |
| Battery charge limit | 80 % |

### Fan curves

Measured on 2026-10-18 with the [Fan curve tuning](../operations/fan-curve-tuning.md) procedure.
Custom curves are disabled on every profile, so the firmware curves apply. Duty cycle on the 0 to
255 scale. At 100 % duty the fans run at about 7410 RPM (CPU) and 7405 RPM (GPU).

| Profile | Fan | Temperatures (°C) | PWM | Custom curve |
| --- | --- | --- | --- | --- |
| Quiet | CPU | 64, 69, 74, 79, 84, 89, 89, 89 | 2, 12, 17, 43, 58, 76, 76, 76 | Disabled |
| Quiet | GPU | 64, 69, 74, 79, 84, 89, 89, 89 | 2, 10, 22, 43, 58, 81, 81, 81 | Disabled |
| Balanced | CPU | 47, 52, 57, 62, 67, 72, 77, 77 | 2, 12, 17, 43, 58, 76, 99, 99 | Disabled |
| Balanced | GPU | 47, 52, 57, 62, 67, 72, 77, 77 | 2, 10, 22, 43, 58, 81, 104, 104 | Disabled |
| Performance | CPU | 43, 48, 53, 58, 63, 68, 73, 78 | 17, 43, 66, 76, 114, 137, 158, 188 | Disabled |
| Performance | GPU | 43, 48, 53, 58, 63, 68, 73, 78 | 22, 43, 63, 81, 119, 145, 160, 196 | Disabled |

Steady state of an all-core load (`cpu` workload of the procedure) on mains power, factory curves:

| Measurement | Quiet | Balanced | Performance |
| --- | --- | --- | --- |
| Tctl | 86.5 °C | 93.2 °C | 95.2 °C |
| Mean CPU clock | 2950 MHz | 3031 MHz | 3674 MHz |
| CPU / GPU fan | 3120 / 3433 RPM | 2812 / 3115 RPM | 6040 / 6261 RPM |

### Energy performance preference

Runtime test of 2026-10-19, Performance platform profile, factory curves, mains power. Idle is
300 s on the idle plateau; load is the mean of 3 runs per setting, alternated in the same window.

| Measurement | `performance` governor and EPP | `powersave` governor, `balance_performance` EPP |
| --- | --- | --- |
| Idle SoC PPT (amdgpu hwmon) | 47.5 W | 25.3 W |
| Idle Tctl | 91.1 °C | 58.6 °C |
| Idle CPU / GPU fan | 6021 / 6270 RPM | 3300 / 3585 RPM |
| `cpu` workload throughput | 14,216 bogo ops/s | 14,226 bogo ops/s |
| `mixed` workload throughput (`cpu` stressor) | 27,726 bogo ops/s | 27,847 bogo ops/s |
| Tctl under load | 95.2 °C | 95.2 °C |
| Status | Applied by power-profiles-daemon | Pending a Nix change |

### asusd profile settings

Learned state in `/etc/asusd/asusd.ron`, not declared in Nix.

| Setting | Value | Effect |
| --- | --- | --- |
| `change_platform_profile_on_ac` | `true` | Switches the platform profile on every charger event |
| `platform_profile_on_ac` | `Performance` | Profile applied when the charger is plugged in |
| `change_platform_profile_on_battery` | `true` | Switches the platform profile when the charger is unplugged |
| `platform_profile_on_battery` | `Quiet` | Profile applied on battery |
| `platform_profile_linked_epp` | `true` | Writes the EPP linked to the profile on every profile change |
| `profile_performance_epp` | `Performance` | EPP written with the Performance profile |
| `profile_balanced_epp` | `BalancePower` | EPP written with the Balanced profile |
| `profile_quiet_epp` | `Power` | EPP written with the Quiet profile |

### Options

| Option | Default | Description |
| --- | --- | --- |
| `custom.nvidia.enable` | `false` | NVIDIA driver, its power management and VA-API video decoding |
| `custom.asus.enable` | `false` | asusd, ROG Control Center, charge limit service |
| `custom.asus.chargeLimit` | `100` | Charge percentage at which charging stops, 20 to 100 |
| `custom.audio.enable` | `false` | PipeWire with ALSA, PulseAudio and JACK layers |
| `custom.peripherals.enable` | `false` | Bluetooth, Logitech receivers, input-remapper |
| `custom.power.enable` | `false` | Power profiles, delayed hibernation, hibernation on critical battery |
| `custom.diskHealth.enable` | `false` | smartd with desktop notifications |

### Upstream documentation

| Subject | Link |
| --- | --- |
| NVIDIA power management | <https://download.nvidia.com/XFree86/Linux-x86_64/595.104.02/README/powermanagement.html> |
| NVIDIA on NixOS | <https://wiki.nixos.org/wiki/Nvidia> |
| nvidia-vaapi-driver | <https://github.com/elFarto/nvidia-vaapi-driver> |
| asusctl | <https://gitlab.com/asus-linux/asusctl> |
| `systemd-sleep.conf` | <https://www.freedesktop.org/software/systemd/man/latest/systemd-sleep.conf.html> |
| `hardware.nvidia` | <https://search.nixos.org/options?channel=unstable&query=hardware.nvidia> |
| `services.asusd` | <https://search.nixos.org/options?channel=unstable&query=services.asusd> |
| `services.pipewire` | <https://search.nixos.org/options?channel=unstable&query=services.pipewire> |
| `hardware.bluetooth` | <https://search.nixos.org/options?channel=unstable&query=hardware.bluetooth> |
| `services.smartd` | <https://search.nixos.org/options?channel=unstable&query=services.smartd> |
| `services.upower` | <https://search.nixos.org/options?channel=unstable&query=services.upower> |
