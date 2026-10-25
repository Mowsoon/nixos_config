# Security

## Overview

The workstation is a single-user laptop. The security design answers three threats, each with its
own layer:

| Threat | Layer | Document |
| --- | --- | --- |
| Theft or physical access while powered off | Secure Boot with custom keys, LUKS2 with TPM2 unlock | [Boot chain](boot-chain.md) |
| Remote attacker or a program leaking data | No inbound port, outbound filtering per executable, encrypted DNS | [Network](network.md) |
| Compromised user program trying to gain root or read the kernel | Kernel hardening, AppArmor, audit, restricted sudo and Nix daemon | This document |

This document covers the third layer and the handling of secrets. The configuration is published
in a public repository, so no secret ever enters it.

### Kernel hardening

The kernel runs the Linux Security Module (LSM) stack `landlock,yama,apparmor,bpf`:

- Landlock lets an unprivileged program sandbox itself.
- Yama restricts `ptrace` to descendants, so a compromised program cannot attach to the browser or
  the password manager of the same user.
- AppArmor confines the programs that ship a profile.
- The BPF LSM lets systemd and other services attach security policies written in eBPF.

The `integrity` name of older kernels no longer exists since kernel 6.9: IMA and EVM register as
their own LSMs and stay inert without a policy.

The sysctl settings close information leaks and reduce the attack surface of the kernel:

- kernel pointers are hidden from every user, and the kernel log is readable by root only, so an
  exploit cannot read kernel addresses to defeat address randomisation;
- unprivileged eBPF is disabled and the eBPF JIT compiler is hardened against JIT spraying;
- `kexec` is disabled, so root cannot replace the running kernel with an unsigned one;
- TTY line disciplines are no longer loaded on demand, removing a source of kernel bugs reachable
  from user space.

Unprivileged user namespaces stay enabled: browser sandboxes, the Claude desktop application and
rootless containers need them. Kernel lockdown stays at `none`. Lockdown in `integrity` mode would
disable hibernation, and gives no protection while nixpkgs kernels load unsigned modules; module
signing is a Phase 8 subject of the migration roadmap.

### Audit

`auditd` records kernel audit events to `/var/log/audit`, persisted with `/var/log`. The kernel
starts auditing from the first instruction (`audit=1`), with a backlog of 1024 events to survive the
burst of early boot.

### Privileges

Users are immutable: `users.mutableUsers = false`, so `passwd` and `useradd` have no lasting effect
and every account is declared. The password of `mowsoon` is a yescrypt hash read from
`/persist/secrets/mowsoon.hash`, outside the repository.

Only members of `wheel` may run `sudo` at all (`execWheelOnly`): the binary is not executable for
other users, which removes it as an attack surface for system accounts. Only members of `wheel` may
talk to the Nix daemon, so a system service account cannot build or fetch anything.

The user is not in the `docker` group. Membership of that group is equivalent to root, because the
daemon mounts any host path into a container on request; Docker commands go through `sudo`.

Hardware access granted through udev stays per device. Packages that ship broad rules, such as
OpenRGB, which tags I2C buses and `/dev/port` for the session user, are installed without them,
and their service receives only the device it drives ([Hardware](hardware.md#lighting)).

Reading the keyboard is the access a keylogger needs, so the lighting effects keep it in a
process of its own. `rgb-keyreader` runs under a dynamic user whose only extra right is the
`rgb-keys` group, read-only on the G915 X evdev node; its cgroup may open input devices in
read-only mode and nothing else, it has a private network namespace with every IP address denied
and Unix sockets as the only family, it writes nowhere and logs only warnings. It forwards key
presses, and the release of the six modifier keys, without history to the one user who owns its
socket; in pulse mode it forwards neither which key was pressed nor any release.

The notification waves rely on a monitor of the session bus, which receives the full content of
every notification: sender, title and text. That access is also kept in a process of its own,
`rgb-notifywatch`, restricted to the `Notify` calls, which forwards only the application name to
the effects daemon, logs nothing of the content, and runs without network or write access. The
feature is off unless `custom.rgb.effects.notifications.enable` is set.

### Software supply

Unfree packages are allowed one by one: each module that needs one adds its name to
`custom.unfreePackages`, and `nixpkgs.config.allowUnfreePredicate` rejects every other unfree
package. `allowUnfree = true` is never set. Unfree packages are not in the public binary cache and
build locally.

Every flake input is pinned by `flake.lock`. Updating it is an explicit commit.

### Secrets

| Secret | Location | Backup |
| --- | --- | --- |
| User password hash | `/persist/secrets/mowsoon.hash` | Password manager holds the password |
| Secure Boot private keys | `/persist/var/lib/sbctl` | Encrypted archive made before each reinstallation |
| LUKS passphrase and recovery key | Not stored on the machine | Password manager |
| LUKS header backup | Not stored on the machine | Password manager attachment |
| BitLocker recovery key | Not stored on the machine | Password manager |
| Wi-Fi secrets, Bluetooth pairing keys | `/persist`, mode `0700` | None, learned again |
| SSH private key | `~/.ssh` in the persistent home | Encrypted archive made before each reinstallation |

`inventory/`, VM firmware variables and emulated TPM state are listed in `.gitignore`, so a local
audit or test artefact cannot be committed by accident.

## How to check the security baseline

1. Check the active LSM stack.

   ```bash
   cat /sys/kernel/security/lsm
   ```

2. Count the AppArmor profiles loaded in the kernel.

   ```bash
   sudo wc -l /sys/kernel/security/apparmor/profiles
   ```

3. Check the hardened sysctl values.

   ```bash
   sysctl kernel.kptr_restrict kernel.dmesg_restrict kernel.unprivileged_bpf_disabled kernel.kexec_load_disabled
   ```

   ```text
   kernel.kptr_restrict = 2
   kernel.dmesg_restrict = 1
   kernel.unprivileged_bpf_disabled = 1
   kernel.kexec_load_disabled = 1
   ```

4. Check that auditd receives events.

   ```bash
   sudo auditctl -s
   ```

   The output shows `enabled 1` and a running `pid`.

## How to allow a new unfree package

1. Add the name returned by `lib.getName` for the package to `custom.unfreePackages`, in the module
   or host file that installs it.

   ```nix
   {
     custom.unfreePackages = [ "terraform" ];
   }
   ```

2. Apply the configuration. The package builds locally.

## Reference

### Kernel parameters and sysctls

| Setting | Value | Effect |
| --- | --- | --- |
| `lsm` | `landlock,yama,apparmor,bpf` | LSM stack |
| `audit` | `1` | Audit from early boot |
| `audit_backlog_limit` | `1024` | Audit queue length |
| `kernel.kptr_restrict` | `2` | Kernel pointers hidden from everyone |
| `kernel.dmesg_restrict` | `1` | Kernel log readable by root only |
| `kernel.unprivileged_bpf_disabled` | `1` | eBPF reserved to privileged users |
| `net.core.bpf_jit_harden` | `2` | eBPF JIT hardening for every user |
| `kernel.kexec_load_disabled` | `1` | No kernel replacement at runtime |
| `dev.tty.ldisc_autoload` | `0` | No on-demand line discipline loading |

### Privilege settings

| Setting | Value |
| --- | --- |
| `users.mutableUsers` | `false` |
| `users.users.mowsoon.extraGroups` | `wheel` |
| `security.sudo.execWheelOnly` | `true` |
| `nix.settings.allowed-users` | `@wheel` |
| Kernel lockdown | `none` |

### Options

| Option | Default | Description |
| --- | --- | --- |
| `custom.hardening.enable` | `false` | AppArmor, audit, sysctls, wheel-only sudo and Nix daemon |
| `custom.unfreePackages` | `[ ]` | Names of the unfree packages allowed to build |

### Upstream documentation

| Subject | Link |
| --- | --- |
| Kernel sysctl reference | <https://docs.kernel.org/admin-guide/sysctl/kernel.html> |
| Linux Security Modules | <https://docs.kernel.org/admin-guide/LSM/index.html> |
| Kernel lockdown | <https://man7.org/linux/man-pages/man7/kernel_lockdown.7.html> |
| `security.apparmor` | <https://search.nixos.org/options?channel=unstable&query=security.apparmor> |
| `security.auditd` | <https://search.nixos.org/options?channel=unstable&query=security.auditd> |
| `security.sudo` | <https://search.nixos.org/options?channel=unstable&query=security.sudo> |
| `nixpkgs.config.allowUnfreePredicate` | <https://search.nixos.org/options?channel=unstable&query=allowUnfreePredicate> |
