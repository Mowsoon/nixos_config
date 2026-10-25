# User environment

## Overview

Everything the user `mowsoon` runs is declared: the shell, the editor, the command-line tools, the
desktop applications and their user services. Home Manager builds this environment from
`home/mowsoon/` and activates it with each system generation. The home directory itself is a
persistent subvolume, so files the user creates survive reboots; the declared configuration files
in it are links into the Nix store, rewritten at each activation.

### Home Manager

Home Manager runs as a NixOS module, configured in `hosts/hephaestus/home.nix`:

- `useGlobalPkgs` makes it use the system `pkgs`, with the same overlays and unfree allowlist;
- `useUserPackages` installs user packages into the user profile of the system generation, so a
  rollback of the system also rolls back the user environment;
- `sharedModules` loads the NixVim Home Manager module.

A file managed by Home Manager is read-only. A change made in an application that tries to write
such a file fails, or is overwritten at the next activation: the change belongs in
`home/mowsoon/`.

### Shell

zsh is the login shell, with completion, autosuggestions, syntax highlighting and the
powerlevel10k prompt. The prompt configuration is the file `home/mowsoon/p10k.zsh`; its instant
prompt block is placed first in `.zshrc` so the prompt appears before the plugins load. The history
saves 20 000 lines, is shared between open shells, and drops duplicates. Aliases make `rm`, `cp`
and `mv` interactive and give short names to the infrastructure clients.

The system side of zsh is declared in `home.nix`: `programs.zsh.enable` installs the shell for
login, and `enableGlobalCompInit = false` leaves completion initialisation to the user
configuration, which avoids running it twice.

### Editor

Neovim is configured with NixVim under `home/mowsoon/editor/`: core options, key mappings and
commands in `cores/`, plugins grouped by role in `plugins/dev`, `plugins/ui` and
`plugins/utils`. Plugins and language servers come from the Nix store; nothing is downloaded at
editor start. Neovim is the default editor through `EDITOR`.
The key mappings are listed in [Editor key mappings](editor-keymaps.md).

### Command-line tools and toolchains

Monitoring, network and file tools, the infrastructure clients (`kubectl`, `helm`, `flux`,
`clusterctl`, `kind`, `terraform`, `azure-cli`, `ansible`), Go and Python are installed globally
for the user. `~/go/bin` is on the `PATH` for tools installed with `go install`.

Other languages and project-specific versions come from the development shell of each project.
direnv with nix-direnv loads that shell when entering the project directory and caches it, so the
shell survives a garbage collection until the project changes.

### Git

Git uses the identity `Mowsoon` and creates repositories on the branch `main`. Commit signing is a
Phase 8 subject of the migration roadmap.

### Desktop applications and user services

Discord, Spotify, LibreOffice and Solaar are user packages. Two user services run in the graphical
session: the OpenSnitch UI, which shows the prompts of the outbound firewall, and EasyEffects, the
audio effects processor. Their own settings are kept in the persistent home.

The EasyEffects input preset `microphone` is declared: `home/mowsoon/audio/microphone.json` holds
it as EasyEffects exports it, Home Manager links it into `~/.local/share/easyeffects/input/`, and
the service loads it at start through the EasyEffects socket. The preset is read-only; a setting
changed in the EasyEffects window is lost at the next start unless it is exported back into the
repository. The chain and its tuning are described in [Hardware](hardware.md).

### Default applications

The association between file types and applications is declared in `home/mowsoon/mime.nix`.
Home Manager writes `~/.config/mimeapps.list` as a read-only link into the store, so the Plasma
"Default Applications" page and the "Remember application association" box of "Open With" no
longer save anything: a new association is a change in Nix. Glob keys such as `image/*` are
expanded at build time against the shared-mime-info database, and an exact key wins over a glob,
which is how `text/html` goes to Firefox while the rest of `text/*` goes to Neovim. Neovim is a
terminal application; Plasma opens it in Konsole.

### Docker

Docker runs as a rootful daemon, started on the first use of its socket rather than at boot. Its
storage is the `@docker` subvolume, excluded from snapshots, and a weekly prune removes every unused
image, container and network. The NVIDIA container toolkit generates a Container Device Interface
(CDI) specification, so containers request the GPU by name. The user is not in the `docker` group:
Docker commands run through `sudo`. The OpenSnitch rule matches `dockerd` and `docker-proxy` of any
moby version.

### Claude desktop application

The Claude desktop application has no nixpkgs package. `pkgs/claude-desktop/package.nix`
repackages the official Debian archive:

- `autoPatchelfHook` rewrites the interpreter and library paths of the Electron binary to point at
  the Nix store;
- a wrapper adds the tools the Cowork virtual machine needs to `PATH` (`qemu`, `virtiofsd`,
  `socat`, `bubblewrap`) and enables the native Wayland backend when `NIXOS_OZONE_WL` is set;
- `chrome-sandbox` stays an ordinary executable: the Electron sandbox relies on unprivileged user
  namespaces instead of a setuid helper.

The application expects OVMF firmware files and `virtiofsd` at Debian paths under `/usr`.
`modules/desktop/claude-desktop.nix` creates these paths as symbolic links into the Nix store with
systemd-tmpfiles at every boot, since the root is rebuilt each time.

The application downloads Claude Code at runtime into `~/.config/Claude/claude-code/`. That binary
is built for a generic Linux distribution and runs through `nix-ld`, which provides a dynamic
loader at the standard path. Its OpenSnitch rule is a pattern that tolerates the version
directories.

## How to add a command-line tool

1. Add the package to `home.packages` in `home/mowsoon/packages.nix`.
2. If the tool opens network connections, add its OpenSnitch rule to
   `hosts/hephaestus/opensnitch.nix`, as described in [Network](network.md).
3. If the package is unfree, add its name to `custom.unfreePackages` in `hosts/hephaestus/home.nix`.
4. Apply the configuration.

## How to use a project development shell

1. Declare the shell in the flake of the project, as `devShells.x86_64-linux.default`.
2. In the project directory, ask direnv to load it.

   ```bash
   echo 'use flake' > .envrc
   direnv allow
   ```

   `direnv allow` approves the content of `.envrc`; direnv refuses an unknown or modified file.

3. Leave and enter the directory again: the tools of the shell appear and disappear with it.

## How to run a container with the GPU

1. Request every NVIDIA device through CDI.

   ```bash
   sudo docker run --rm --device nvidia.com/gpu=all ubuntu nvidia-smi
   ```

## How to update the Claude desktop application

1. Set `version` in `pkgs/claude-desktop/package.nix` to the new release.
2. Download the new archive into the store and print its hash.

   ```bash
   nix-prefetch-url https://downloads.claude.ai/claude-desktop/apt/stable/pool/main/c/claude-desktop/claude-desktop_<version>_amd64.deb
   ```

   `<version>` is the new release, such as `2.26454.2`.

3. Copy the printed hash into `sha256`, then apply the configuration.

## Reference

### Files under `home/mowsoon/`

| File | Content |
| --- | --- |
| `default.nix` | Imports and `home.stateVersion` |
| `shell.nix` | zsh, history, aliases, powerlevel10k |
| `p10k.zsh` | Prompt configuration generated by `p10k configure` |
| `git.nix` | Git identity and defaults |
| `packages.nix` | Command-line tools, toolchains, direnv |
| `audio.nix` | EasyEffects service and its declared input preset |
| `audio/microphone.json` | EasyEffects input preset for the built-in microphone |
| `desktop.nix` | Desktop applications, OpenSnitch UI |
| `mime.nix` | Default applications, zathura, mpv |
| `shortcuts.nix` | Plasma global shortcuts: KRunner and the G keys of the G915 X |
| `editor/nixvim.nix` | NixVim entry point |
| `editor/cores/` | Options, key mappings, commands, colour scheme |
| `editor/plugins/` | Plugins grouped in `dev`, `ui` and `utils` |

### Shell aliases

| Alias | Command |
| --- | --- |
| `rm` | `rm -I --preserve-root` |
| `cp` | `cp -i` |
| `mv` | `mv -i` |
| `ll`, `la` | `ls -l`, `ls -la` |
| `k` | `kubectl` |
| `f` | `flux` |
| `cctl` | `clusterctl` |
| `tf` | `terraform` |
| `sudo` | `sudo` followed by a space, so aliases expand after `sudo` |
| `nrt`, `nrs`, `nrb` | `nixos-rebuild test`, `switch`, `boot` on `#hephaestus` with `--elevate sudo` |
| `nrbr` | `nrb`, then `systemctl reboot` when it succeeds |
| `nrr` | `sudo nixos-rebuild switch --rollback` |
| `nkern` | Booted and current kernel paths; a difference means a reboot is pending |
| `cdn` | `cd ~/.config/nixos` |
| `hib`, `sus`, `sush` | `systemctl hibernate`, `suspend`, `suspend-then-hibernate` |
| `jb`, `jbu <unit>` | `journalctl -b`, `journalctl -b --no-pager -u <unit>` |
| `jke` | `journalctl -k -p err`, kernel messages of priority error and above |
| `gst`, `gaa`, `gcm` | `git status`, `git add -A`, `git commit -m` |
| `ns <pkg>...` | Shell function: `nix shell nixpkgs#<pkg>...` |

### Docker settings

| Setting | Value |
| --- | --- |
| `virtualisation.docker.enableOnBoot` | `false`, socket activation |
| `virtualisation.docker.autoPrune` | Weekly, `--all` |
| `hardware.nvidia-container-toolkit.enable` | Follows `custom.nvidia.enable` |
| Storage | `/var/lib/docker` on the `@docker` subvolume |

### Claude desktop paths

| Path | Content |
| --- | --- |
| `/usr/share/OVMF/OVMF_CODE_4M.fd` | Link to the OVMF code firmware |
| `/usr/share/OVMF/OVMF_VARS_4M.fd` | Link to the OVMF variable template |
| `/usr/bin/virtiofsd` | Link to `virtiofsd` |
| `~/.config/Claude/claude-code/<version>/<hash>/claude` | Claude Code binary, run through `nix-ld` |

### Default applications

| Types | Application |
| --- | --- |
| `text/html`, `application/xhtml+xml`, `http`, `https`, `about` and unknown URL schemes | Firefox |
| `text/*` except HTML, JSON, XML, YAML, TOML, shell scripts | Neovim |
| `application/pdf` | zathura with the MuPDF plugin |
| `image/*` | Gwenview |
| `video/*`, `audio/*` | mpv |
| `inode/directory` | Dolphin |
| Zip, tar, compressed tar, gzip, 7z, RAR | Ark |

### Options

| Option | Default | Description |
| --- | --- | --- |
| `custom.docker.enable` | `false` | Docker daemon, socket activation, weekly prune, NVIDIA CDI |
| `custom.claudeDesktop.enable` | `false` | Claude desktop application, Cowork paths, `nix-ld` |

### Upstream documentation

| Subject | Link |
| --- | --- |
| Home Manager manual | <https://nix-community.github.io/home-manager/> |
| Home Manager options | <https://nix-community.github.io/home-manager/options.xhtml> |
| NixVim options | <https://nix-community.github.io/nixvim/> |
| nix-direnv | <https://github.com/nix-community/nix-direnv> |
| NVIDIA CDI | <https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/cdi-support.html> |
| nix-ld | <https://github.com/nix-community/nix-ld> |
| `virtualisation.docker` | <https://search.nixos.org/options?channel=unstable&query=virtualisation.docker> |
| `programs.nix-ld` | <https://search.nixos.org/options?channel=unstable&query=programs.nix-ld> |
| `services.easyeffects` | <https://nix-community.github.io/home-manager/options.xhtml#opt-services.easyeffects.enable> |
| `xdg.mimeApps` | <https://nix-community.github.io/home-manager/options.xhtml#opt-xdg.mimeApps.enable> |
| MIME applications specification | <https://specifications.freedesktop.org/mime-apps-spec/latest/> |
