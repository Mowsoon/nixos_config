# Storage

## Overview

The Linux disk holds an EFI System Partition (ESP) and one LUKS2 container. Inside the container,
a single Btrfs filesystem is split into subvolumes with different lifetimes: the root is erased at
every cold boot, the Nix store is rebuilt from the configuration, and only a few subvolumes keep
data that cannot be declared. The container and the boot sequence are described in
[Boot chain](boot-chain.md).

### Subvolumes and their lifetime

| Subvolume | Mount point | Lifetime |
| --- | --- | --- |
| `@root` | `/` | Erased at every cold boot, archived 30 days under `old_roots/` |
| `@nix` | `/nix` | Kept; content is reproducible from the flake |
| `@persist` | `/persist` | Kept and snapshotted; holds declared state only |
| `@home` | `/home` | Kept and snapshotted |
| `@log` | `/var/log` | Kept, not snapshotted |
| `@docker` | `/var/lib/docker` | Kept, not snapshotted |
| `@swap` | `/swap` | Kept; holds the swapfile |

Every subvolume except `@swap` is mounted with `compress=zstd:3` and `noatime`. Discards reach
the SSD through the LUKS container (`allowDiscards`) and Btrfs issues them asynchronously by
default.

### Persistence

The root starts empty, so `/etc` and `/var` are rebuilt from the Nix store at each activation.
What cannot be rebuilt falls into three classes: identity (`/etc/machine-id`, user IDs),
secrets (Secure Boot keys, the password hash) and learned state (Bluetooth pairings, Wi-Fi
profiles, OpenSnitch rules accepted at runtime). Only these classes are persisted.

A module that owns such a path adds it to `custom.persistence.directories`. The impermanence
module then bind-mounts `/persist/<path>` onto `<path>` early in boot, before the services start.
Configuration is never persisted: a setting that can be written in Nix is written in Nix, and a
file edited by hand under `/etc` disappears at the next boot by design.

`/home`, `/persist` and `/var/log` are mounted from the initrd (`neededForBoot`), because the
activation runs there and needs the password hash and the home directory.

### Snapshots

snapper takes hourly snapshots of `/home` and `/persist` into their `.snapshots` subvolumes and
keeps 24 hourly, 7 daily and 4 weekly ones. `/nix`, `/var/log` and `/var/lib/docker` are not
snapshotted: the store is reproducible, logs are append-only, and container images are
disposable. A snapshot lives on the same disk: it protects against a mistake, not against a disk
failure.

### Memory and swap

Two swap devices coexist. zram, a compressed swap device in RAM sized to half of the memory, has
priority 100 and absorbs memory pressure without disk I/O. The 32 GiB swapfile in `@swap` has
priority 0: it receives pages only when zram is full, and it holds the hibernation image.

The kernel settings follow from zram being the first swap device. zswap is disabled on the kernel
command line, so pages are not compressed twice. `vm.swappiness = 180` makes the kernel prefer
swapping anonymous pages to zram over dropping the page cache, since a zram swap-in costs less
than a disk read. `vm.page-cluster = 0` disables swap read-ahead, useless on a device without seek
time. systemd-oomd watches the memory pressure of user slices and kills the offending application
before the whole session freezes.

### Maintenance

| Task | Schedule | Scope |
| --- | --- | --- |
| Btrfs scrub | Monthly | The whole filesystem, started from `/nix` |
| TRIM | Weekly, NixOS default | Every mounted filesystem that supports it |
| snapper cleanup | Daily | `/home` and `/persist` |
| Docker prune | Weekly | Unused images, containers and networks |
| Nix garbage collection | Weekly, through `nh clean` | Generations beyond the last 10 and older than 14 days |
| Nix store deduplication | Daily | Identical store files replaced by hard links |
| SMART checks | Continuous, through smartd | Both NVMe disks |

### Windows volume

The Windows disk is a separate NVMe device with its own ESP and a BitLocker-encrypted volume.
Linux never opens it at boot. The crypttab entry is `noauto` and `read-only`: the volume is
unlocked with the BitLocker recovery key only when its mount unit is started, and the
device-mapper mapping itself refuses writes. The mount uses the kernel `ntfs` driver with
`ro,nosuid,nodev,noexec`. The disk is hidden from udisks, so the desktop file manager cannot
offer to mount it read-write.

Read-only access is a safety rule, not a preference: writing to an NTFS volume that Windows left
in a hibernated or fast-startup state corrupts it, and a Linux hibernation with the volume mounted
would do the same in the other direction. No key file is stored on Linux, so root access to Linux
does not grant access to Windows.

## How to persist a new directory

1. Check that the path holds identity, a secret or learned state. If its content can be expressed
   as Nix options, declare it instead.
2. Add the path to `custom.persistence.directories` in the module that owns the service, inside
   its existing `custom` block. Use an attribute set when the directory needs a specific owner or
   mode.

   ```nix
   {
     custom.persistence.directories = [
       {
         directory = "/var/lib/iwd";
         mode = "0700";
       }
     ];
   }
   ```

3. If the directory already holds data, copy it into `/persist` before applying the
   configuration. Once applied, the bind mount hides the original content.

   ```bash
   sudo mkdir -p /persist<directory>
   sudo cp -a <directory>/. /persist<directory>/
   ```

   `<directory>` is the absolute path of the persisted directory, such as `/var/lib/iwd`.

4. Apply the configuration, then check that the directory is a mount point.

   ```bash
   findmnt <directory>
   ```

## How to find state the next boot will erase

1. Mount the top level of the Btrfs filesystem read-only.

   ```bash
   sudo mkdir -p /mnt/btrfs-top
   sudo mount -o subvolid=5,ro /dev/mapper/cryptroot /mnt/btrfs-top
   ```

2. List the files written to the ephemeral root since boot. Persisted directories and other
   subvolumes appear as empty mount points, so every listed file is lost at the next boot.

   ```bash
   sudo find /mnt/btrfs-top/@root -type f
   ```

3. Unmount the top level.

   ```bash
   sudo umount /mnt/btrfs-top
   ```

## How to recover a file from a previous boot

1. Mount the top level read-only, as in the previous procedure.
2. List the archived roots. Each name is the time the root was archived.

   ```bash
   sudo ls /mnt/btrfs-top/old_roots
   ```

3. Copy the file out of the archive, then unmount.

   ```bash
   sudo cp -a /mnt/btrfs-top/old_roots/<timestamp>/<path> <destination>
   sudo umount /mnt/btrfs-top
   ```

   `<timestamp>` is the archive name, `<path>` the path of the file relative to `/`, and
   `<destination>` where the copy goes.

## How to restore a file from a snapshot

1. List the snapshots of the configuration that holds the file, `home` or `persist`.

   ```bash
   sudo snapper -c home list
   ```

2. Copy the file from the snapshot directory.

   ```bash
   sudo cp -a /home/.snapshots/<number>/snapshot/<path> <destination>
   ```

   `<number>` is the snapshot number from the list, `<path>` the path relative to `/home`.

## How to read the Windows volume

1. Start the mount unit. systemd asks for the BitLocker recovery key.

   ```bash
   sudo systemctl start mnt-windows.mount
   ```

2. Read the files under `/mnt/windows`.
3. Unmount the volume and close the encrypted mapping.

   ```bash
   sudo systemctl stop mnt-windows.mount systemd-cryptsetup@windows.service
   ```

## Reference

### Persisted paths

| Path | Owner module | Class |
| --- | --- | --- |
| `/etc/machine-id` | `core/persistence.nix` | Identity |
| `/var/lib/nixos` | `core/persistence.nix` | Identity, stable user and group IDs |
| `/var/lib/systemd` | `core/persistence.nix` | Learned state: timers, random seed, coredumps |
| `/var/lib/sbctl` | `security/secure-boot.nix` | Secret |
| `/etc/NetworkManager/system-connections` | `network/manager.nix` | Secret, mode `0700` |
| `/var/lib/NetworkManager` | `network/manager.nix` | Learned state |
| `/var/lib/iwd` | `network/manager.nix` | Secret, mode `0700` |
| `/var/lib/chrony` | `network/time.nix` | Learned state: clock drift, NTS cookies |
| `/var/lib/opensnitch` | `network/opensnitch.nix` | Learned state: rules accepted in the UI |
| `/var/lib/bluetooth` | `hardware/peripherals.nix` | Secret: pairing keys |
| `/var/lib/power-profiles-daemon` | `hardware/power.nix` | Learned state |
| `/etc/asusd` | `hardware/asus.nix` | Learned state: fan curves, profiles |

`/persist/secrets/mowsoon.hash` is read directly from `/persist` by
`users.users.mowsoon.hashedPasswordFile` and is not bind-mounted.

### Swap devices

| Device | Size | Priority | Role |
| --- | --- | --- | --- |
| zram, zstd | 50 % of RAM | 100 | First swap target |
| `/swap/swapfile` | 32 GiB | 0 | Overflow and hibernation image |

### Kernel memory settings

| Setting | Value | Set by |
| --- | --- | --- |
| `zswap.enabled` | `0` | Kernel command line |
| `vm.swappiness` | `180` | sysctl |
| `vm.page-cluster` | `0` | sysctl |
| systemd-oomd | User slices | `systemd.oomd.enableUserSlices` |

### Options

| Option | Default | Description |
| --- | --- | --- |
| `custom.persistence.enable` | `false` | Bind-mounts the persisted paths |
| `custom.persistence.root` | None | Mount point of the persistent subvolume |
| `custom.persistence.directories` | `[ ]` | Paths contributed by modules; strings or impermanence attribute sets |
| `custom.snapshots.enable` | `false` | Creates the snapper configurations |
| `custom.snapshots.subvolumes` | None | Configuration names mapped to mount points |
| `custom.memory.enable` | `false` | zram, zswap off, swap sysctls, systemd-oomd on user slices |
| `custom.windowsVolume.enable` | `false` | crypttab entry, mount unit and udisks rule |
| `custom.windowsVolume.device` | None | Encrypted block device of the Windows volume |
| `custom.windowsVolume.type` | `bitlk` | crypttab format, `bitlk` or `luks` |
| `custom.windowsVolume.diskSerial` | `null` | Serial of the Windows disk, hidden from udisks |
| `custom.windowsVolume.mountPoint` | `/mnt/windows` | Mount point of the unlocked volume |

### Upstream documentation

| Subject | Link |
| --- | --- |
| disko | <https://github.com/nix-community/disko> |
| impermanence | <https://github.com/nix-community/impermanence> |
| Btrfs | <https://btrfs.readthedocs.io/en/latest/> |
| snapper | <http://snapper.io/documentation.html> |
| zram | <https://docs.kernel.org/admin-guide/blockdev/zram.html> |
| `zramSwap` | <https://search.nixos.org/options?channel=unstable&query=zramSwap> |
| `services.snapper` | <https://search.nixos.org/options?channel=unstable&query=services.snapper> |
| `systemd.oomd` | <https://search.nixos.org/options?channel=unstable&query=systemd.oomd> |
| `environment.persistence` | <https://github.com/nix-community/impermanence#module-usage> |
