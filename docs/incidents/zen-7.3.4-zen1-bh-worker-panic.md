# linux-zen 7.3.4-zen1 panics in the BH workqueue

## Overview

On 2026-11-14, the update gate ran the failure drills against the update of `nixos-unstable` from
2026-11-01 to 2026-11-11. The candidate system built, but every drill failed: the VM that writes
the disk image of the drill machine panicked as soon as disko opened the LUKS container.

```text
+ cryptsetup open /dev/disk/by-partlabel/disk-main-luks cryptroot --allow-discards
  --perf-no_read_workqueue --perf-no_write_workqueue ...
BUG: kernel NULL pointer dereference, address: 0000000000000138
CPU: 13 UID: 0 PID: 0 Comm: swapper/13 Tainted: G            E       7.3.4-zen1 #1-NixOS
RIP: 0010:process_one_work+0xb5/0x3d0
Call Trace:
 <IRQ>
 bh_worker+0x1a6/0x1d0
 tasklet_action+0x10/0x30
 handle_softirqs+0xde/0x290
Kernel panic - not syncing: Fatal exception in interrupt
```

The update moves `linuxPackages_zen` from 7.2.14 to 7.3.4-zen1. That release carries a duplicated
`worker->current_at` store in `process_one_work()`, left by a merge of the zen scheduler tree. The
store runs outside the `if (worker->task)` check, so it dereferences a NULL task for every BH
worker, which has none. dm-crypt without its workqueues (`bypassWorkqueues`, the setting of the
`hephaestus` container) completes its work in a BH worker, and so does a tasklet of any driver: the
zen report shows the same panic at boot from the xHCI controller, without dm-crypt. The workstation
would very likely panic when it unlocks its root, before any generation of it could be tested.
Mainline 7.3.4 is not affected.

| Component | Version |
| --- | --- |
| `nixos-unstable` | 2026-11-11, `d4f25a3` |
| `linux-zen` | 7.3.4-zen1, panics; 7.2.14 in the running system |
| Fixed in | 7.3.4-zen2, published by zen on 2026-11-11 |

Cause: a regression of the zen kernel, upstream.

Decision: wait. The update of `linux_zen` to 7.3.4-zen2 is merged in nixpkgs `master` and has
reached `nixos-unstable-small` and `nixpkgs-unstable`, but not yet `nixos-unstable`, which has not
moved since the morning of 2026-11-11. The update is not accepted: `flake.lock` stays on
2026-11-01.

Exit condition: `nixos-unstable` contains nixpkgs pull request 586820. Run the update gate again;
the drills must pass on 7.3.4-zen2 before the update is accepted.

## How to check whether nixos-unstable carries the fix

1. Ask GitHub whether the merge commit of the pull request is an ancestor of the channel.

   ```bash
   curl -s https://api.github.com/repos/NixOS/nixpkgs/compare/9ca0e988a4f8873321cadb02d8c39eaad15a3378...nixos-unstable | jq -r .status
   ```

   `behind` means the channel does not carry it yet; `ahead` or `identical` means it does.

2. Run the update gate again and check that the kernel of `diff.log` reads `7.3.4-zen2` or later.

   ```bash
   nix run .#update-gate
   ```

## Reference

| Source | Content |
| --- | --- |
| [zen-kernel issue 425](https://github.com/zen-kernel/zen-kernel/issues/425) | Same panic at `process_one_work+0xb5/0x3d0`, cause and fix `ba87bc0` |
| [nixpkgs pull request 586820](https://github.com/NixOS/nixpkgs/pull/586820) | `linux_zen: 7.3.4-zen1 -> 7.3.4-zen2`, merged 2026-11-11 |
| [nixpkgs pull request 586563](https://github.com/NixOS/nixpkgs/pull/586563) | `linux_zen: 7.2.15 -> 7.3.4`, the change that brought the panic |
| [dm-crypt](https://docs.kernel.org/admin-guide/device-mapper/dm-crypt.html) | `no_read_workqueue` and `no_write_workqueue` |
| [Update gate](../operations/update-gate.md) | The run that found the failure and how it is triaged |
