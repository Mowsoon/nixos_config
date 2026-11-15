# Second reseal in one boot

## Overview

On 2026-11-15, the boot asked for the passphrase of the root container, and the policy update
unit failed with:

```text
pcr12.errors.EnrollError: the TPM2 slot no longer unlocks the container: run 'pcr12 reseal --ask-key' and type the recovery key
```

The day before, two rebuilds ran in the same boot. Each installed a generation with a new
stub, so the install hook rewrote the pcrlock policy and its copy on the ESP twice, and each
rewrite changed the PCR 12 of the next boot. The first reseal unlocked the container with the
only TPM2 slot, sealed to the PCR 12 of the running boot, enrolled a slot sealed to the next PCR 12
and wiped the old one. The second reseal had to unlock with that new slot, whose PCR 12 the
running boot did not have: `systemd-cryptenroll` refused with `TPM policy does not match current
system state`, the slot stayed sealed to the PCR 12 of the first rewrite, and the next boot
measured the PCR 12 of the second.

The failure was printed by the rebuild only, as `Failed to install bootloader`. No notification
was shown: only the systemd units recorded their failures in `/run/pcr12/alert`, not the install
hook.

Cause: the reseal kept a single TPM2 slot, so the running boot lost its own slot at the first
reseal. The drills reboot between two policy changes and never ran two in one boot.

Decision: `pcr12` keeps the slot sealed to the running boot until the next reboot, next to the
slot of the next boot, and the reseal at boot wipes the slot left from the previous boot. The
install hook appends its failures to `/run/pcr12/alert` like the units. The `same-boot-reseal`
drill changes the policy three times in one boot, reboots without a prompt and checks the alert
of a refused reseal in the hook. It failed on the previous code with the error above, and passes.

## How to recover from it

1. Before the next reboot, renew the slot with the passphrase or the recovery key:

   ```bash
   sudo pcr12 reseal --ask-key
   ```

2. Reboot. The container opens without a prompt.

## Reference

| Source | Content |
| --- | --- |
| [Boot chain](../architecture/boot-chain.md#credentials-lock) | The two TPM2 slots and the reseal |
| [LUKS enrollment](../operations/luks-enrollment.md) | The slots of the container and their replacement |
| [Failure drills](../operations/failure-drills.md) | The `same-boot-reseal` drill |
