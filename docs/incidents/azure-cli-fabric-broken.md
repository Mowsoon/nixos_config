# Azure CLI blocked by fabric

## Overview

On 2026-11-03, the update of `nixos-unstable` from 2026-10-06 to 2026-11-01 stopped at
evaluation:

```text
error: Refusing to evaluate package 'python3.14-fabric-3.2.3' because it has problems:
- broken: This package is broken.
```

`azure-cli` 2.91.0 depends on the Python package fabric, which nixpkgs marks broken since invoke,
its task library, reached version 3: fabric 3.2.3 does not support it yet. The configuration does
not use fabric directly; the trace of the evaluation, with `--show-trace`, leads from
`home-manager-path` to `python3.14-azure-cli-2.91.0`.

Affected configuration:

| Component | Version |
| --- | --- |
| `nixos-unstable` | 2026-11-01, `0bb2eed` |
| `azure-cli` | 2.91.0 |
| fabric | 3.2.3, broken with invoke 3 |

Cause: a package failure upstream, not a change of the configuration.

Decision: `azure-cli` is removed from `home/mowsoon/dev/infra.nix` until it evaluates again. It
was not in use, so the rest of the update lands without it. Pinning it from the previous nixpkgs
revision through an overlay was not needed.

Exit condition: put `azure-cli` back once fabric is no longer marked broken in `nixos-unstable`, or
once `azure-cli` no longer depends on it.

## How to check whether azure-cli evaluates again

1. After a `nix flake update`, evaluate the package from the locked nixpkgs. The command prints a
   store path once fabric is fixed, and the same `broken` error otherwise.

   ```bash
   nix eval --raw ~/.config/nixos#nixosConfigurations.hephaestus.pkgs.azure-cli.outPath
   ```

2. When it prints a path, add `azure-cli` back to `home.packages` in
   `home/mowsoon/dev/infra.nix`, restore its name in the tools paragraph of
   `docs/architecture/user-environment.md`, and record the date and the nixpkgs revision of the
   return in the Overview of this file.

## Reference

| Source | Content |
| --- | --- |
| [fabric issue 2376](https://github.com/fabric/fabric/issues/2376) | Support of invoke 3, cited by the `broken` condition in nixpkgs |
| [nixpkgs PR tracker](https://nixpk.gs/pr-tracker.html) | Whether a fixing pull request has reached `nixos-unstable` |
| [nixpkgs problems handling](https://nixos.org/manual/nixpkgs/unstable#sec-problems) | `broken` packages and how evaluation refuses them |
