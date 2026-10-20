# Fan curve tuning

## Overview

The workstation is a performance machine: it runs virtual machines and local Kubernetes clusters
for long periods, and noise does not matter. The goal of fan tuning is the highest sustained
all-core CPU throughput on mains power, not a lower temperature for its own sake. A fan curve is
kept only when repeated measurements prove it beats the factory curve.

The firmware has three platform profiles, Quiet, Balanced and Performance, switched by
power-profiles-daemon through asusd. Each profile has a factory curve per fan (CPU and GPU) and
can carry a custom eight-point curve, temperature to duty cycle. Custom curves are learned state
of asusd, stored in the persisted `/etc/asusd`, and are not declared in Nix: a store link would be
read-only to asusd.

The idle state depends on the profile. In Performance, power-profiles-daemon sets the CPU energy
performance preference (EPP) to `performance`: cores stay in boost and the SoC draws about 50 W at
idle. Tctl sits at the 95 °C target of the firmware even at idle, with the fans near 6000 RPM on
the factory curve. In Balanced, the same machine idles at about 22 W and 55 to 62 °C. A high idle
temperature in Performance is therefore expected and is not a reason to stop.

Each fan curve follows its own sensor: the CPU fan follows the CPU temperature, the GPU fan the
GPU temperature. Under a CPU-only load the GPU stays at 40 to 45 °C. A custom GPU curve shaped
on CPU temperatures therefore runs the GPU fan slower than the factory curve does, and moves less
air through the shared heat pipes.

The batteries of 2026-10-18 and 2026-10-19 closed the question for this machine: the factory
curves stay on every profile. The best candidate, C2, ran both fans at full speed under load and
gained 1.65 to 2.83 % of CPU throughput against same-window factory runs, on both sides of the
2 % threshold, and never met the criteria on both workloads in the same comparison. Its cost does
not depend on the load: the GPU temperature is the same at idle and under a CPU load, 35 to
45 °C, so any GPU curve that keeps the GPU fan high under load also keeps it high at idle.

asusd acts on the platform profile and the EPP alongside power-profiles-daemon. When the charger
is plugged in it switches the platform profile to Performance (`change_platform_profile_on_ac`),
when it is unplugged to Quiet (`change_platform_profile_on_battery`), and on every profile change
it writes the EPP linked to the profile (`platform_profile_linked_epp`), all set in
`/etc/asusd/asusd.ron`. Plugging or unplugging the charger during a battery therefore
changes the profile under test without any action of the runner. On 2026-10-19 a charger plugged
in during a Balanced cooldown turned it into Performance for 30 minutes.

Background applications distort idle measurements. Discord and Spotify keep one or two cores in
boost at 4.1 to 4.6 GHz: on mains power, Balanced then idles near 95 °C and 40 W, and the cooldown
of step 3 never reaches its plateau below 70 °C.

Throughput drifts with the room temperature: on 2026-10-18, factory runs made overnight were
2.6 % faster than the same runs made in the evening. A drift of that size is larger than the
2 % acceptance threshold, so a candidate is only compared with factory runs made in the same
conditions.

Fans only help when the limit is thermal. If the CPU clock drops while its temperature stays
below the thermal ceiling, the limit is the power envelope of the firmware, and no fan curve
changes the result. The procedure therefore measures the limit before it tunes anything.

This procedure is written to be run end to end by an agent on the workstation, such as Claude
Code. It treats the machine as a production system: every claim in the final report rests on
repeated runs and raw logs kept with the report.

## How to run the test battery

Blast radius: the CPU runs at full load for several hours in total. Nothing is written outside
`~/fan-tuning/` except the fan curves through `asusctl`. Rollback: reset the curves of a profile
to the factory values with `asusctl` (see `asusctl fan-curve --help`).

1. Prepare the conditions and record them in the report: mains power connected, lid open, laptop
   on a hard flat surface, no other heavy process, room temperature read from a thermometer at
   the start and at the end of each battery. Close Discord and Spotify. Connect the charger
   before the battery and leave it connected until the end, then check that it is online.

   ```bash
   cat /sys/class/power_supply/ADP0/online
   ```

   ```text
   1
   ```

2. Write a sampling script in `~/fan-tuning/` that appends one CSV line per second with every
   metric listed in the Reference section, then a load runner that starts the sampler, runs one
   workload, stops the sampler and keeps the workload output. The run identifier (profile, curve,
   workload, repetition) is part of every file name. Before each run, the runner reads back the
   platform profile, governor and EPP of every CPU; after it, the runner marks the run invalid if
   any of them changed in its log.
3. Before each run, switch to the Balanced profile and let the machine cool until it reaches its
   idle plateau: Tctl has moved by less than 1 °C over the last 60 seconds and is below 70 °C.
   Then switch to the profile under test and start the workload. Every run starts from the same
   thermal state. Do not wait for an absolute temperature such as 50 °C: this laptop idles at
   55 to 62 °C in Balanced and never reaches it.
4. Measure the baseline: for each profile, with the factory curves, run each workload of the
   Reference section three times.
5. Analyse the baseline over the steady-state window only. For each run, compute the mean CPU
   clock, mean and maximum Tctl, mean fan speeds and the workload throughput; for each profile and
   workload, the mean and standard deviation over the three repetitions.
6. Identify the limit of the Performance profile:
   - thermal: Tctl reaches its ceiling (about 95 °C) and the clock falls while the temperature
     holds, and the fans are below their maximum speed: continue at step 7;
   - power: the clock falls or stays flat while Tctl stays clearly below the ceiling, or the fans
     already run at full speed: stop tuning, report the evidence and skip to step 10.
7. Tune only the curves of the Performance profile, CPU and GPU fans together, since they share
   the heat pipes. Start from a steeper CPU curve that reaches 100 % between 75 and 80 °C, and a
   GPU curve that reaches 100 % at a GPU temperature of 40 °C, since the GPU stays at 40 to 45 °C
   under a CPU load. Apply both with `asusctl`, read them back to confirm they are active, then
   run every workload three times.
8. Iterate at most four candidate curves. Keep a candidate only if it meets the acceptance
   criteria of the Reference section against the baseline. Stop iterating once a candidate runs
   both fans at full speed in steady state: no other curve adds cooling under sustained load.
9. Validate the best candidate with three more repetitions of every workload, run after the
   others, each one alternated with a factory run of the same workload in the same time window.
   Decide on the comparison with these control runs, not with the baseline, since the room
   temperature drifts over a battery.
10. Recommend the default profile on mains power, based on the baseline and the validation runs.
    The switch is a Plasma energy setting (AC profile) and is left to the user.
11. Write the report in `~/fan-tuning/report.md` with the content listed in the Reference
    section, then propose the update of the Plasma energy and fan curve tables in
    `docs/architecture/hardware.md`. Do not commit.

## Reference

### Safety rules

| Rule | Reason |
| --- | --- |
| Change curves only through `asusctl`, never by editing `/etc/asusd` while asusd runs | asusd overwrites its files and owns their format |
| Never set a duty cycle below the factory curve at 70 °C or above | The firmware curve is the thermal safety floor |
| Never set a fan to 0 % | No passive cooling is possible under load |
| Stop the load at once if Tctl stays at or above 98 °C for more than 10 seconds, or any sensor reports a critical value | Margin under the 100 °C limit of the CPU; single-core boost spikes of 94 °C on one CCD are normal |
| Do not change power limits (PPT, SPL) or undervolt | Hardware risk, decided separately by the user |
| Do not change the Nix configuration | Curves are mutable state; the repository only documents them |

### Metrics

| Metric | Source |
| --- | --- |
| Timestamp | `date +%s.%N` |
| Platform profile | `/sys/firmware/acpi/platform_profile` |
| Governor and EPP | Distinct values of `scaling_governor` and `energy_performance_preference` over `/sys/devices/system/cpu/cpu*/cpufreq/` |
| Tctl, Tccd1, Tccd2 | hwmon device named `k10temp`, `temp*_input` in millidegrees |
| CPU and GPU fan speed | hwmon device named `asus`, `fan*_input` in RPM |
| Mean CPU clock | Mean of `/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq`, in kHz |
| GPU temperature and power | `nvidia-smi --query-gpu=temperature.gpu,power.draw --format=csv,noheader,nounits` |
| Workload throughput | `stress-ng --metrics-brief` output, bogo operations per second |

Find hwmon devices by their `name` file, never by their number, which changes between boots.

### Workloads

| Name | Command | Represents |
| --- | --- | --- |
| `cpu` | `stress-ng --cpu 0 --cpu-method matrixprod --metrics-brief --timeout 600s` | Compute-bound guests |
| `mixed` | `stress-ng --cpu 0 --vm 4 --vm-bytes 25% --metrics-brief --timeout 600s` | Guests that stress memory as well |

Run the tools with `nix shell nixpkgs#stress-ng nixpkgs#lm_sensors -c <command>`. The steady-state
window is the last 300 seconds of each 600-second run.

### Acceptance criteria

A candidate curve replaces the factory curve only if both hold for every workload:

| Criterion | Threshold |
| --- | --- |
| Throughput gain | Mean gain of at least 2 % over the baseline, and larger than twice the larger standard deviation of the two |
| No regression | No workload loses throughput beyond its baseline standard deviation |

The throughput of a workload is the bogo operations per second of its `cpu` stressor. The `vm`
figure of `mixed` is reported but not judged: it is bound by memory, not by temperature, and no
fan curve moves it beyond its noise.

A curve that only lowers temperatures at equal throughput is reported but not applied.

Runs made in different sessions are comparable only when the room temperature of both sessions,
read from a thermometer, is within 1 °C. Otherwise the comparison requires control runs
alternated in the same time window.

### Report content

| Section | Content |
| --- | --- |
| Conditions | Date, room temperature from a thermometer at the start and end, power source, kernel, driver and firmware versions |
| Limit diagnosis | Thermal or power, with the clock and Tctl figures that prove it |
| Results | One table per workload: configuration, repetitions, mean and standard deviation of throughput, clock, Tctl and fan speeds |
| Curves | Factory curves and every candidate, as read back from `asusctl` |
| Decision | Applied curve or none, recommended default profile, with the criteria they meet |
| Raw data | Paths of every CSV log and workload output kept in `~/fan-tuning/` |
