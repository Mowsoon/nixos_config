# Failure drills refused by the by-name OVMFFull

## Overview

On 2026-11-14, the update gate built the candidate of the update of `nixos-unstable` from
2026-11-01 to 2026-11-11, but every failure drill failed to evaluate:

```text
error: function 'anonymous lambda' called with unexpected argument 'httpSupport'
       at «github:NixOS/nixpkgs/d4f25a3...»/pkgs/by-name/ov/OVMFFull/package.nix:1:1:
```

The `firmware-update` drill boots a second firmware build to change PCR 0. It obtained it with
`OVMFFull.override { httpSupport = false; }`. `OVMFFull` used to be `OVMF.override { ... }` in
`all-packages.nix`, so its `override` reached the arguments of OVMF. nixpkgs moved it to
`pkgs/by-name`, as a package whose own arguments are only `OVMF` and `stdenv`, and the override
now targets an argument that does not exist. The drill machine is shared by every drill, so all
eleven failed with it.

| Component | Version |
| --- | --- |
| `nixos-unstable` | 2026-11-11, `d4f25a3` |
| nixpkgs change | `OVMFFull` moved to by-name, 2026-11-03 |

Cause: a change of a nixpkgs interface used by this repository, not a broken package.

Decision: the drill calls `OVMF.override` with the arguments of `OVMFFull` and `httpSupport`
turned off. On the previous nixpkgs, this gives the same derivation as the former override, so
the drill still tests the same firmware; on the new one, it still differs from `OVMFFull`. The
eleven drills evaluate against the candidate.

## Reference

| Source | Content |
| --- | --- |
| [nixpkgs pull request 582501](https://github.com/NixOS/nixpkgs/pull/582501) | `OVMF{,Full}: migrate to by-name` |
| [Failure drills](../operations/failure-drills.md) | The `firmware-update` drill and the shared drill machine |
| [Update gate](../operations/update-gate.md) | The run that found the failure and how it is triaged |
