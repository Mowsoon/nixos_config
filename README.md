# nixos_config

Declarative NixOS configuration that replaces the Arch Linux installation on the second boot entry
of a dual-boot workstation. Every change is validated in a QEMU virtual machine before it reaches
the physical host.

## Overview

The repository is a Nix flake pinned to `nixos-unstable`. Each machine is a host under `hosts/`.

| Host | Role |
| --- | --- |
| `vm-test` | Disposable QEMU machine used to validate the configuration |
| `hephaestus` | Physical workstation, tested through its `vmWithDisko` variant |

Procedures run by hand on the workstation are documented under [docs](docs/README.md).

## Getting started

Prerequisites: Nix with the `nix-command` and `flakes` experimental features enabled.

1. Generate the password hash of the `mowsoon` user for the test machine.

   ```bash
   nix shell nixpkgs#mkpasswd -c mkpasswd -m yescrypt > hosts/vm-test/mowsoon.hash
   ```

2. Track every file so the flake can see it.

   ```bash
   git add -A
   ```

3. Validate formatting, lint and evaluation.

   ```bash
   nix flake check
   ```

4. Build and start the test machine.

   ```bash
   nix build .#nixosConfigurations.vm-test.config.system.build.vm
   ./result/bin/run-vm-test-vm
   ```

The machine reaches a login prompt in the terminal. Press `Ctrl+A` then `X` to stop it.

## Reference

| Command | Effect |
| --- | --- |
| `nix fmt` | Formats every Nix file with `nixfmt` |
| `nix flake check` | Runs `nixfmt --check`, `statix`, `deadnix` and evaluates every host |
| `nix develop` | Opens a shell with `nixfmt-tree`, `statix`, `deadnix` and `mkpasswd` |
| `nix flake update` | Moves `flake.lock` to the latest `nixos-unstable` revision |
