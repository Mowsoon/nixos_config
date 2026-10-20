# nixos_config

Declarative NixOS configuration of a dual-boot workstation, an ASUS ROG Strix G17 laptop that runs
Windows on a second disk. The configuration replaced an Arch Linux installation on 2026-10-17.
Every change is validated in a QEMU virtual machine before it reaches the physical host.

## Overview

The repository is a Nix flake pinned to `nixos-unstable`. Each machine is a host under `hosts/`.

| Host | Role |
| --- | --- |
| `hephaestus` | Physical workstation, also bootable as a disko VM with its `vmWithDisko` variant |
| `hephaestus-rehearsal` | `hephaestus` retargeted at the virtual disk of the installation rehearsal |
| `installer` | Live USB image used to install `hephaestus` |
| `vm-test` | Disposable QEMU machine used to validate the base configuration |

The system boots through Secure Boot with custom keys, unlocks its encrypted disk with the TPM,
and erases its root filesystem at every boot: only declared state persists. Outbound traffic is
filtered per executable and DNS is encrypted. The design of each part is described in
[docs/architecture](docs/architecture/overview.md); procedures and incidents are indexed in
[docs](docs/README.md).

## Getting started

Prerequisites: Nix with the `nix-command` and `flakes` experimental features enabled.
The `hephaestus` systems also import a private input that a fork cannot read; see [Build without
the private repository](docs/architecture/overview.md#how-to-build-without-the-private-repository).

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
| `nix run .#hephaestus-vm` | Builds the `hephaestus` disko VM and boots it from a blank firmware and TPM |
| `nix run .#rehearsal` | Boots the installer image against a blank disk to rehearse the installation |
| `nix build .#nixosConfigurations.installer.config.system.build.isoImage` | Builds the installer image |
| `nixos-rebuild test --flake .#hephaestus --elevate sudo` | Runs a new generation on the workstation until the next reboot |
| `nixos-rebuild switch --flake .#hephaestus --elevate sudo` | Runs a new generation and makes it the boot default |
| `nixos-rebuild boot --flake .#hephaestus --elevate sudo` | Makes a new generation the boot default without running it |
| `nix flake update` | Moves `flake.lock` to the latest `nixos-unstable` revision |
