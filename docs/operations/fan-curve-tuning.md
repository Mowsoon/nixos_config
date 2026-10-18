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
preference to `performance`: cores stay in boost and the SoC draws about 50 W at idle, with Tctl
around 85 to 90 °C. In Balanced, the same machine idles at about 22 W and 55 to 62 °C. A high
idle temperature in Performance is therefore expected and is not a reason to stop.

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
   on a hard flat surface, no other heavy process, room temperature noted.
2. Write a sampling script in `~/fan-tuning/` that appends one CSV line per second with every
   metric listed in the Reference section, then a load runner that starts the sampler, runs one
   workload, stops the sampler and keeps the workload output. The run identifier (profile, curve,
   workload, repetition) is part of every file name.
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
   the heat pipes. Start from a steeper curve that reaches 100 % between 75 and 80 °C, apply it
   with `asusctl`, read it back to confirm it is active, then run every workload three times.
8. Iterate at most four candidate curves. Keep a candidate only if it meets the acceptance
   criteria of the Reference section against the baseline.
9. Validate the best candidate with three more repetitions of every workload, run after the
   others, to confirm the gain is stable over time.
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

A curve that only lowers temperatures at equal throughput is reported but not applied.

### Report content

| Section | Content |
| --- | --- |
| Conditions | Date, room temperature, power source, kernel, driver and firmware versions |
| Limit diagnosis | Thermal or power, with the clock and Tctl figures that prove it |
| Results | One table per workload: configuration, repetitions, mean and standard deviation of throughput, clock, Tctl and fan speeds |
| Curves | Factory curves and every candidate, as read back from `asusctl` |
| Decision | Applied curve or none, recommended default profile, with the criteria they meet |
| Raw data | Paths of every CSV log and workload output kept in `~/fan-tuning/` |
