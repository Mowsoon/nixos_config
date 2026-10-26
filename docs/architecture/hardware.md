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
thermal target at the same clock.

This pairing is declared. power-profiles-daemon starts with `--block-driver=amd_pstate`: it
still switches the platform profile for Plasma, but no longer writes the governor or the EPP. The
governor is fixed to `powersave`, under which amd-pstate follows the EPP. asusd alone writes the
EPP linked to each profile, and `custom.asus.performanceEpp` sets the one of the Performance
profile to `balance_performance`.

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
- `NVreg_DynamicPowerManagement = 0` turns off runtime D3, which powers the GPU down while the
  panel is off. With the MUX on the discrete GPU it saved nothing measurable, and waking the GPU
  from it during the console switch before sleep deadlocked the driver
  ([incident](../incidents/sleep-after-hibernation-deadlock.md)).

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

USB keyboards and mice wake the machine from sleep, but a `system-sleep` hook disarms their wakeup
for the duration of hibernation, and chrony no longer fires RTC interrupts: a wakeup event that
reaches the platform while it enters S4 leaves the laptop powered on with the image already written
([incident](../incidents/hibernation-wakeup-hang.md)).

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

That file stays learned state, written by asusd itself, for instance when the charge limit is
applied. One value is declared on top of it: before asusd starts, a pre-start script rewrites
`profile_performance_epp` to `custom.asus.performanceEpp`. The script runs outside the sandbox of
the unit (`+` prefix): the system call filter of asusd kills `sed -i`, which calls `fchown` to
keep the owner of the file it rewrites. If the line is missing, after an asusd
update that renames it, the script fails and asusd does not start, so the change cannot go
unnoticed. On the very first boot, before asusd has created the file, the script does nothing and
the value applies from the next start.

The battery charge limit is declared instead: a oneshot service, `asus-charge-limit`, applies
`custom.asus.chargeLimit` through `asusctl` at every boot, after asusd starts. The limit is 80 %,
which slows battery wear on a laptop that stays plugged in.

### Audio

PipeWire is the audio server, with its ALSA, PulseAudio and JACK compatibility layers and
WirePlumber as session manager. rtkit grants it real-time scheduling. Device access goes through
the logind seat of the session. The effects processor, EasyEffects, runs as a user service
declared in the user environment.

The built-in microphone is a digital microphone on the Realtek ALC294 codec, exposed as the
`analog-input-mic` route of the Ryzen HD Audio controller. The AMD audio coprocessor (ACP) also
has a PDM microphone interface, but its machine driver does not bind on this model: the G713PI is
absent from the DMI quirk table of `snd-soc-acp6x-mach`, and a test build that forced it timed
out when starting the DMA. The codec path is the one in use, as it was on the previous Arch
installation.

The ACP and the HD Audio controller are two functions of one audio block that the firmware powers
off in sleep. Its ACPI methods race when both functions resume at the same time, and the controller
then stays unpowered until the next boot. `custom.audio.serializeAmdAcpResume` makes the kernel
suspend and resume both functions one after the other
([incident](../incidents/amd-acp-hda-resume-race.md)).

The capture gain is the sum of two codec controls, `Capture` and `Mic Boost`, which WirePlumber
drives from the volume of the source. At 100 % they add 60 dB, enough for the low-frequency room
noise to saturate the converter, and the signal then looks like random full-scale noise. The
source volume is 0.30: `Capture` at +28.5 dB, `Mic Boost` at 0 dB and no software gain, which
leaves about 4 dB of headroom on normal speech. WirePlumber stores this value in
`~/.local/state/wireplumber`; it is not declared, so a client that resets the volume to 100 %
undoes it.

EasyEffects processes the microphone with the declared input preset `microphone`, tuned for voice
calls on the laptop speakers in a room with steady fan and appliance noise. The echo canceller
comes first, while the signal is still linear, so it can subtract what the speakers play. It needs
a few seconds of far-end audio to adapt, and it attenuates the local voice while both sides talk at
once. A microphone test that plays the voice straight back to the speakers, such as the one of
Discord, keeps it in that state and sounds choppy: it is not a valid listening test without
headphones. DeepFilterNet replaces RNNoise, which removed the unvoiced consonants at the end of
words. The expander only attenuates what stays below the speech level, with a long release that
keeps word endings, and the limiter comes last. Discord receives the processed signal through the
virtual source "Easy Effects Source", with its own noise suppression, echo cancellation and
automatic gain control off.

EasyEffects moves every recording stream to its virtual source. A recording that must read the
raw microphone, for a measurement, sets `node.dont-move` on its stream.

### Peripherals

BlueZ runs with its experimental features, which report the battery level of Bluetooth headsets
to Plasma. Pairing keys are persisted. The udev rules for Logitech wireless receivers let Solaar
configure the devices without root.

The G keys of the G915 X send F13 to F21 from the onboard profile of the keyboard; the Fn key never
leaves the keyboard. XKB turns those keys into symbols Plasma already uses: F13 opens the system
settings, F20 mutes the microphone, F21 toggles the touchpad, and F19 has no symbol at all. The
laptop sends the same F21 for its own touchpad key, and its ROG and function keys use `PROG1` to
`PROG4`. A udev hwdb entry, matched on the G915 X only, rewrites the nine scan codes into keys whose
symbols are free on this desktop, so the laptop keys and the Windows profile stay as they are.

### Lighting

The OpenRGB SDK server drives the lighting of the Logitech G915 X through its LIGHTSPEED receiver
and listens on the loopback address only. The keyboard backlight of the laptop stays with asusd:
OpenRGB ships a detector for the same ASUS controller, and two daemons writing to it would fight.
The server therefore runs under a dynamic user that can open only the hidraw nodes of the receiver,
granted through the `openrgb-receiver` group by a single udev rule. The upstream udev rules of
OpenRGB are left out: besides thousands of RGB devices, they give the session user the ASUS
controller, every I2C bus and `/dev/port`, which is raw access to the processor I/O ports. No
OpenRGB state is persisted; its configuration is regenerated at every boot.

The keyboard stores nothing that OpenRGB sends. Frames are volatile: the keyboard keeps the last
frame while powered, and plays its own onboard effect after a power cycle when the server is
stopped. While the server runs, it takes control back at every reconnection of the keyboard and
repaints only the LEDs it believes changed, so a client must send one complete frame after each
connection and each wake-up, or keys keep stale colours from the keyboard buffer. OpenRGB mirrors
the idle timers of the keyboard: it dims after one minute without a key press, stops sending
frames and puts the keyboard to sleep after five, and resumes on the next key press. Frames do not
keep the keyboard awake.

The radio carries about 320 HID++ packets per second, each acknowledged in about 2 ms. OpenRGB
groups keys by colour and sends only what changed, so the frame rate depends on how many colours
change per frame, not on the rate the client asks for; frames above the ceiling are dropped, not
queued.

The lighting effects that drive the server are described in
[Desktop](desktop.md#keyboard-lighting-effects).

### Wi-Fi

The MediaTek MT7922 card runs the `mt7921e` driver of the mt76 family. The in-tree driver resumes
from hibernation as from sleep and waits for a firmware that the power cut has stopped, which logs
a restore timeout on every resume. The mt7921 module rebuilds the mt76 directory of the kernel
source with a patch that gives the driver a separate restore callback, against the cached kernel,
and installs it ahead of the in-tree modules
([incident](../incidents/mt7921e-hibernation-restore.md)).

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
   grep -E 'EnableS0ixPowerManagement|UseKernelSuspendNotifiers|PreserveVideoMemoryAllocations|DynamicPowerManagement:' /proc/driver/nvidia/params
   ```

   ```text
   PreserveVideoMemoryAllocations: 1
   EnableS0ixPowerManagement: 1
   UseKernelSuspendNotifiers: 0
   DynamicPowerManagement: 0
   ```

## How to test a driver or kernel option

1. Change the option in the module, then install the generation as the next boot entry.

   ```bash
   nixos-rebuild boot --flake ~/.config/nixos#hephaestus --elevate sudo
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

## How to read the code sent by a key

1. Print the raw events of the keyboard.

   ```bash
   sudo nix run nixpkgs#evtest -- /dev/input/<event>
   ```

   `<event>` is the event node of the keyboard, such as `event10`, listed by
   `sudo nix run nixpkgs#libinput -- list-devices`.

2. Press the key. The `MSC_SCAN` value is the scan code matched by hwdb, and the `EV_KEY` line
   shows the kernel key it is translated into.

3. After a hwdb change, apply it to the connected keyboard without a reboot.

   ```bash
   sudo udevadm trigger --subsystem-match=input --action=change
   ```

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
| Wi-Fi | MediaTek MT7922, `mt7921e` driver |
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
| `NVreg_DynamicPowerManagement` | `0` |
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
| `services.power-profiles-daemon.enable` | `true`, started with `--block-driver=amd_pstate` |
| `powerManagement.cpuFreqGovernor` | `powersave` |
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
| Status | Former power-profiles-daemon pairing | Declared |

### asusd profile settings

Learned state in `/etc/asusd/asusd.ron`; only `profile_performance_epp` is enforced from Nix.

| Setting | Value | Effect |
| --- | --- | --- |
| `change_platform_profile_on_ac` | `true` | Switches the platform profile on every charger event |
| `platform_profile_on_ac` | `Performance` | Profile applied when the charger is plugged in |
| `change_platform_profile_on_battery` | `true` | Switches the platform profile when the charger is unplugged |
| `platform_profile_on_battery` | `Quiet` | Profile applied on battery |
| `platform_profile_linked_epp` | `true` | Writes the EPP linked to the profile on every profile change |
| `profile_performance_epp` | `BalancePerformance`, from `custom.asus.performanceEpp` | EPP written with the Performance profile |
| `profile_balanced_epp` | `BalancePower` | EPP written with the Balanced profile |
| `profile_quiet_epp` | `Power` | EPP written with the Quiet profile |

### Built-in microphone

| Item | Value |
| --- | --- |
| PipeWire source | `alsa_input.pci-0000_09_00.6.analog-stereo`, route `analog-input-mic` |
| Codec pin | ALC294 node `0x12`, fixed internal digital microphone |
| Source volume | 0.30 |
| `Capture` | 61 of 63, +28.5 dB |
| `Mic Boost` | 0 of 3, 0 dB |
| Room noise | Mostly below 80 Hz, hiss above 12 kHz |

### Microphone input chain

| Order | Stage | Settings | Purpose |
| --- | --- | --- | --- |
| 1 | Echo canceller | WebRTC, echo cancellation and high-pass on, noise suppression and AGC off | Removes the speaker output from the microphone |
| 2 | DeepFilterNet | Attenuation limit 40 dB | Removes the steady background noise, keeps consonants |
| 3 | Expander | Downward, threshold -50 dB, ratio 3, attack 5 ms, release 200 ms, sidechain RMS with 100 Hz high-pass | Attenuates the residual noise between words |
| 4 | Equalizer | High-pass 90 Hz, -2 dB at 250 Hz, +2 dB at 3 kHz, low-pass 14 kHz | Removes rumble and hiss, reduces boxiness, adds presence |
| 5 | Compressor | Downward, threshold -30 dB, ratio 3, attack 10 ms, release 120 ms, makeup 11 dB | Evens out the voice and brings it to the target loudness |
| 6 | De-esser | Split above 5 kHz, threshold -22 dB, ratio 3 | Softens sibilants |
| 7 | Limiter | Threshold -1.5 dB, x4 oversampling, gain boost off | Caps the true peak |

### Microphone measurements

Read text followed by 10 s of silence, recorded at the source volume of 0.30. The noise floor is
the RMS level of the silence, the loudness and true peak are measured on the speech.

| Measure | Target | Raw | Processed |
| --- | --- | --- | --- |
| Noise floor | Below -60 dBFS | -47.5 dBFS | -97.3 dBFS |
| Integrated loudness | About -18 LUFS | -25.7 LUFS | -18.6 LUFS |
| True peak | -1 dBTP or lower | -6.9 dBTP | -1.5 dBTP |
| Speaker echo, voice played at speaker volume 0.40 | Inaudible | -22.4 LUFS | -70 LUFS |

### G915 X lighting measurements

Measured through the OpenRGB SDK server, counting the HID++ writes on the receiver with `strace`.

| Item | Value |
| --- | --- |
| Addressable LEDs | 121: 106 keys in a 6 by 21 AZERTY matrix, 15 extras (media keys, G1 to G9, logo) |
| Firmware modes | Off, Static, Breathing, Spectrum Cycle, Color Wave, Ripple (reacts to key presses) |
| Radio throughput | About 320 packets per second, one packet every 3.0 ms |
| Acknowledgement latency | 2.0 ms median, 6 ms at the 99th percentile |
| Full frame, every LED a different colour | 32 packets, about 10 frames per second |
| Uniform colour | 4 packets, about 70 frames per second |
| A few keys changing on a fixed background | 3 to 7 packets, 22 to 30 frames per second |
| Idle and sleep timers | 1 minute (dim), 5 minutes (sleep), read from the keyboard |
| Rated battery life | 36 h at full brightness, 90 h at half, 800 h with lighting off |

### G915 X G keys

The hwdb entry matches the LIGHTSPEED product `40B5` and the wired product `C356`.

| Key | Scan code | Kernel key | XKB symbol | Plasma shortcut name |
| --- | --- | --- | --- | --- |
| G1 | `70068` | `KEY_F14` | `XF86Launch5` | `Launch (5)` |
| G2 | `70069` | `KEY_F15` | `XF86Launch6` | `Launch (6)` |
| G3 | `7006a` | `KEY_F16` | `XF86Launch7` | `Launch (7)` |
| G4 | `7006b` | `KEY_F17` | `XF86Launch8` | `Launch (8)` |
| G5 | `7006c` | `KEY_F18` | `XF86Launch9` | `Launch (9)` |
| G6 | `7006d` | `KEY_SCALE` | `XF86LaunchA` | `Launch (A)` |
| G7 | `7006e` | `KEY_DASHBOARD` | `XF86LaunchB` | `Launch (B)` |
| G8 | `7006f` | `KEY_FINANCE` | `XF86Finance` | `Finance` |
| G9 | `70070` | `KEY_SHOP` | `XF86Shop` | `Shop` |

### Options

| Option | Default | Description |
| --- | --- | --- |
| `custom.nvidia.enable` | `false` | NVIDIA driver, its power management and VA-API video decoding |
| `custom.asus.enable` | `false` | asusd, ROG Control Center, charge limit service |
| `custom.asus.chargeLimit` | `100` | Charge percentage at which charging stops, 20 to 100 |
| `custom.asus.performanceEpp` | `null` | EPP that asusd writes with the Performance profile, enforced in `asusd.ron` before asusd starts |
| `custom.audio.enable` | `false` | PipeWire with ALSA, PulseAudio and JACK layers |
| `custom.audio.serializeAmdAcpResume` | `false` | `power/async` disabled on the revision `0x62` ACP and the AMD HD Audio controller |
| `custom.peripherals.enable` | `false` | Bluetooth, Logitech receivers, G915 X key remapping |
| `custom.rgb.enable` | `false` | OpenRGB SDK server on `127.0.0.1:6742`, confined to the Logitech LIGHTSPEED receiver |
| `custom.power.enable` | `false` | Power profiles without CPU driver, `powersave` governor, delayed hibernation, hibernation on critical battery |
| `custom.power.disarmInputWakeupForHibernation` | `false` | `system-sleep` hook that disables the wakeup of USB HID devices during hibernation |
| `custom.diskHealth.enable` | `false` | smartd with desktop notifications |
| `custom.mt7921.enable` | `false` | mt76 Wi-Fi modules rebuilt with the MT7921 hibernation restore patch |

### Upstream documentation

| Subject | Link |
| --- | --- |
| NVIDIA power management | <https://download.nvidia.com/XFree86/Linux-x86_64/595.104.02/README/powermanagement.html> |
| NVIDIA on NixOS | <https://wiki.nixos.org/wiki/Nvidia> |
| nvidia-vaapi-driver | <https://github.com/elFarto/nvidia-vaapi-driver> |
| asusctl | <https://gitlab.com/asus-linux/asusctl> |
| OpenRGB | <https://gitlab.com/CalcProgrammer1/OpenRGB> |
| G915 X specifications | <https://www.logitechg.com/en-gb/products/gaming-keyboards/g915-x-wireless-mechanical-gaming-keyboard.html> |
| `systemd-sleep.conf` | <https://www.freedesktop.org/software/systemd/man/latest/systemd-sleep.conf.html> |
| `hardware.nvidia` | <https://search.nixos.org/options?channel=unstable&query=hardware.nvidia> |
| `services.asusd` | <https://search.nixos.org/options?channel=unstable&query=services.asusd> |
| `services.hardware.openrgb` | <https://search.nixos.org/options?channel=unstable&query=services.hardware.openrgb> |
| EasyEffects | <https://github.com/wwmm/easyeffects> |
| DeepFilterNet | <https://github.com/Rikorose/DeepFilterNet> |
| `services.pipewire` | <https://search.nixos.org/options?channel=unstable&query=services.pipewire> |
| `hardware.bluetooth` | <https://search.nixos.org/options?channel=unstable&query=hardware.bluetooth> |
| hwdb | <https://www.freedesktop.org/software/systemd/man/latest/hwdb.html> |
| `services.udev.extraHwdb` | <https://search.nixos.org/options?channel=unstable&query=services.udev.extraHwdb> |
| `services.smartd` | <https://search.nixos.org/options?channel=unstable&query=services.smartd> |
| `services.upower` | <https://search.nixos.org/options?channel=unstable&query=services.upower> |
