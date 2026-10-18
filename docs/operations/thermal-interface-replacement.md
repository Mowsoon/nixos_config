# Thermal interface replacement

## Overview

ASUS ships the ROG Strix G17 (2023, G713) with Thermal Grizzly Conductonaut Extreme liquid metal
on the CPU and thermal paste on the GPU, and notes that the liquid metal version may vary by
configuration. Liquid metal does not dry like paste, but it can migrate or be absorbed by the
cooler surface over the years; paste pumps out under thermal cycling. A replacement is planned
maintenance, done when the measurements show a degradation or as preventive work after a few
years of use.

The decision rests on measurements, not on a single reading. A Ryzen 7045HX is designed to run up
to its temperature limit under load, and the Performance profile keeps it hot at idle (see
[Fan curve tuning](fan-curve-tuning.md)). Signs that point at the thermal interface are a
sustained clock that falls while Tctl sits at its ceiling, a gap between Tccd1 and Tccd2 that
grows over a long all-core load, or a regression against earlier measurements in the same
conditions. The idle state on 2026-10-18, 55 to 62 °C with both CCDs within 2 °C in Balanced,
showed no such sign.

Liquid metal conducts electricity: a drop on a nearby component causes a short circuit. ASUS
surrounds the die with a thin barrier sponge. Opening the laptop may void the warranty depending
on the country and the purchase date.

## How to replace the thermal interface

Blast radius: the whole laptop. A liquid metal spill can destroy the motherboard. Rollback: none
once the cooler is removed; prepare every material before opening.

1. Measure the baseline with the [Fan curve tuning](fan-curve-tuning.md) procedure, steps 1 to 6,
   in the Performance profile, and keep the report.
2. Gather every item of the Materials table, and the disassembly guide for this exact model
   (ASUS service documentation or a G713 teardown guide). Do not work from a guide for another
   chassis.
3. Shut the laptop down completely, not into sleep or hibernation, unplug the charger, and
   disconnect the battery connector before touching the cooler.
4. Remove the cooler as the guide describes. Keep the screws in their order, and note the
   position and thickness of every thermal pad that comes off with it.
5. Clean the old liquid metal from the die and the cooler with cotton swabs and isopropyl alcohol.
   The copper contact area stays grey after cleaning: do not sand it.
6. Check the barrier sponge around the CPU die. If it is damaged, cover the small components around
   the die with Kapton tape.
7. Apply a thin, even layer of liquid metal on the CPU die and on the matching cooler surface, as
   the product instructions describe. No bead, no excess at the edges.
8. Clean the GPU die and place the phase-change pad on it.
9. Replace any torn thermal pad with one of the same thickness, measured with a caliper, or with
   thermal putty.
10. Refit the cooler, tightening its screws in the order printed next to them, reconnect the
    battery and boot.
11. Run a few heat cycles (the phase-change pad reaches its performance after melting once), then
    measure again with the same procedure and compare the reports.

## Reference

### Materials

| Item | Product | Note |
| --- | --- | --- |
| CPU interface | Thermal Grizzly Conductonaut Extreme, 1 g | Same product as the factory; replacing liquid metal with paste costs sustained performance |
| GPU interface | Honeywell PTM7950 phase-change pad | Does not pump out under thermal cycling |
| Thermal pads | Pads of the measured thickness, or thermal putty | Only if a pad tears; never guess the thickness |
| Cleaning | Isopropyl alcohol of at least 99 %, cotton swabs, lint-free wipes | Removes liquid metal and old paste |
| Protection | Kapton tape | Covers the components around the CPU die if the barrier sponge is damaged |
| Tools | Precision Phillips screwdrivers (PH0, PH00), plastic spudger, caliper | No metal tool near the liquid metal |

### Sources

| Subject | Link |
| --- | --- |
| Liquid metal in ROG laptops, per model | <https://rog.asus.com/articles/rog-gaming-laptops/celebrating-three-years-of-liquid-metal-in-rog-laptops/> |
