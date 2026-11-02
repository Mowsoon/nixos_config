# Kernel development

## Overview

Kernel work for hephaestus (power limits, module signing, BPF schedulers and policies) is written
against upstream trees and tested in a virtual machine before it reaches the workstation. A Nix
build of the kernel starts from scratch at every change, which takes over half an hour for the
zen configuration, so the development loop builds incrementally in a source tree, from a
development shell of the flake. A finished patch reaches hephaestus through `boot.kernelPatches`
on the zen kernel, where Nix builds it reproducibly.

The source tree is a blobless clone of mainline: it holds the whole history of commits and trees,
and fetches the content of an old file only when a command needs it. A patch for a subsystem is
written against the tree of that subsystem, added as a git worktree of the same clone: each tree
has its own working directory and they share one object store.

Builds run out of tree (`make O=`) into `~/src/kernel/build/<tree>`. `~/src/kernel/build` is a
nested Btrfs subvolume, created by a user tmpfiles rule from `home/mowsoon/dev/kernel.nix`, so
the gigabytes of objects of a build stay out of the hourly snapshots of `/home`, while the sources
stay in them.

The `kernel` development shell carries the toolchain of the zen kernel package (compilers, Rust,
`pahole` for BTF), clang and llvm for the BPF selftests, `bpftool`, QEMU, b4 and git with
`send-email`. It exports `KERNEL_BASE_CONFIG`, the configuration of the zen kernel that hephaestus
runs, so a build starts from the options the workstation actually uses.

A build is tested in `kernel-test`, a variant of `vm-test` where root is logged in on the serial
console and `~/src/kernel` is shared on `/src` through virtiofs. `nix run .#kernel-vm` boots its
NixOS initrd and userspace on the `bzImage` of a build directory, through the
`NIXPKGS_QEMU_KERNEL_kernel_test` variable of the NixOS VM script: nothing is installed and the
ESP is never touched.

The initrd and the NixOS userspace carry the modules of the NixOS kernel, which a kernel of
another version cannot load. The VM build therefore has no module to load: `make localyesconfig`
turns every module that the VM loads on the NixOS kernel into a built-in and disables all the
others. The list of those modules is the `kernel-vm-modules` package of the flake, the `lsmod` of
`kernel-test` recorded by a NixOS test, so it follows the VM configuration and nixpkgs.

Bugs that corrupt memory or locks rarely crash where they happen. A debug build adds the kernel
checkers that catch them at the faulty access, at the cost of speed and memory, so it is used
only in the VM. The fragment `kernel/debug.config` of this repository turns on KASAN (every memory
access checked against a shadow map), lockdep (every lock order checked against the orders seen
so far), the atomic sleep check and kmemleak (a scan for allocations nothing points to any more),
with their self-tests. The lockdep self-tests run at every boot. The KASAN KUnit suite makes one
deliberate invalid access per case and passes only when KASAN reports it; it is built in but runs
only with `kunit.enable=1` on the kernel command line, because its deliberate faults, such as a
free through a pointer one byte past an allocation, also trip kmemleak, which then disables
itself. The kmemleak sample that leaks on purpose exists only as a module, which the VM build
cannot load, so it is left out.

A test run needs no typing in the VM. Given a script as second argument, `kernel-vm` copies it to
`~/src/kernel/build/vm/run` and adds three parameters to the kernel command line:
`systemd.run=` makes systemd run it at boot, `systemd.setenv=KERNEL_BUILD=` hands it the path of
the build directory inside the VM, and `systemd.run_success_action=poweroff` with its failure
counterpart power the VM off afterwards. On NixOS `default.target` is an alias of
`multi-user.target`, through which the generated unit is not started, so `kernel-test` pulls it
in from `multi-user.target`; without `systemd.run=` that unit does not exist and nothing happens.
The script writes its results into the build directory, which is why the tree is shared writable.

The kselftests of a subsystem declare the options they need in a `config` fragment next to them.
A selftests build merges those fragments into the VM configuration and turns every remaining
module into a built-in with `mod2yesconfig`. The kselftest build skips `bpf` and `sched_ext`
unless `SKIP_TARGETS` is emptied. Two subsystems cannot be tested in this VM: `cpufreq` and
`amd-pstate` need a CPU frequency driver and a real AMD processor, which QEMU does not expose, so
they belong to the hardware steps. Suspend and hibernation are exercised through
`/sys/power/pm_test`, which walks the sleep path up to a chosen level and returns without
sleeping; only the `freezer` level passes here, because virtiofs, which carries the Nix store and
`/src`, cannot suspend or freeze its devices (`virtio_pci_freeze returns -95`). Testing the deeper
levels needs a VM whose store lives on a disk image.

## How to set up the source tree

Blast radius: none outside `~/src/kernel`.

1. Clone mainline without the content of old files.

   ```bash
   mkdir -p ~/src/kernel
   git clone --filter=blob:none https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git ~/src/kernel/mainline
   ```

2. Check that the build directory is a subvolume: a subvolume root always has inode number 256.

   ```bash
   stat -c %i ~/src/kernel/build
   ```

   If the directory is missing, apply the configuration once (`nixos-rebuild test`), which runs
   the tmpfiles rules of Home Manager.

## How to add a subsystem tree

1. Add the subsystem repository as a remote and fetch it.

   ```bash
   git -C ~/src/kernel/mainline remote add <remote> <url>
   git -C ~/src/kernel/mainline fetch --filter=blob:none <remote>
   ```

2. Check out its branch in its own worktree.

   ```bash
   git -C ~/src/kernel/mainline worktree add ~/src/kernel/<remote> <remote>/<branch>
   ```

`<remote>` names the tree, such as `pdx86`. `<url>` and `<branch>` come from the `MAINTAINERS`
entry of the subsystem, line `T:`.

## How to configure and build a tree

1. Open the kernel shell and go to the tree.

   ```bash
   nix develop ~/.config/nixos#kernel
   cd ~/src/kernel/<tree>
   ```

   `<tree>` is `mainline` or a worktree name.

2. Start from the zen configuration and adapt it to the tree. The store copy is read-only, hence
   the `chmod`.

   ```bash
   mkdir -p ../build/<tree>
   cp "$KERNEL_BASE_CONFIG" ../build/<tree>/.config
   chmod u+w ../build/<tree>/.config
   make O=../build/<tree> olddefconfig
   ```

3. Build the kernel and its modules. After a change, run the same command again: only what
   depends on the changed files is rebuilt, and most of the time goes into walking the tree.

   ```bash
   make O=../build/<tree> -j"$(nproc)"
   ```

   A single module target, such as `drivers/platform/x86/asus-armoury.ko`, fails at the
   `modpost` stage, and a directory target compiles the objects without linking the modules: the
   full `make` is the command of the loop.

## How to boot a build in the VM

1. In the kernel shell, configure a VM build of the tree: the zen configuration, then only the
   modules the VM loads, built in. `yes ""` accepts the default of every question.

   ```bash
   mkdir -p ../build/<tree>-vm
   cp "$KERNEL_BASE_CONFIG" ../build/<tree>-vm/.config
   chmod u+w ../build/<tree>-vm/.config
   make O=../build/<tree>-vm olddefconfig
   yes "" | make O=../build/<tree>-vm LSMOD="$(nix build --no-link --print-out-paths ~/.config/nixos#kernel-vm-modules)/lsmod" localyesconfig
   make O=../build/<tree>-vm -j"$(nproc)"
   ```

2. Boot it. The VM disk lives in `~/src/kernel/build/vm`, out of the snapshots.

   ```bash
   nix run ~/.config/nixos#kernel-vm -- ~/src/kernel/build/<tree>-vm
   ```

3. In the VM, check the running kernel and the shared tree, then power off.

   ```bash
   uname -r
   ls /src
   poweroff
   ```

## How to boot a debug build in the VM

1. In the kernel shell, start from the VM configuration of the tree and merge the fragment.
   `merge_config.sh -m` merges without running the configurator, and `olddefconfig` resolves the
   new dependencies.

   ```bash
   mkdir -p ../build/<tree>-debug
   cp ../build/<tree>-vm/.config ../build/<tree>-debug/.config
   scripts/kconfig/merge_config.sh -m -O ../build/<tree>-debug ../build/<tree>-debug/.config ~/.config/nixos/kernel/debug.config
   make O=../build/<tree>-debug olddefconfig
   make O=../build/<tree>-debug -j"$(nproc)"
   ```

2. Boot it.

   ```bash
   nix run ~/.config/nixos#kernel-vm -- ~/src/kernel/build/<tree>-debug
   ```

   `QEMU_KERNEL_PARAMS` adds parameters to the kernel command line: `log_buf_len=16M` enlarges
   the kernel log, so the early self-test results are not pushed out by later reports.

   ```bash
   QEMU_KERNEL_PARAMS="log_buf_len=16M" nix run ~/.config/nixos#kernel-vm -- ~/src/kernel/build/<tree>-debug
   ```

3. In the VM, read the lockdep self-test result and run one kmemleak scan.

   ```bash
   dmesg | grep -E 'testcases passed|kmemleak: Kernel'
   echo scan > /sys/kernel/debug/kmemleak
   cat /sys/kernel/debug/kmemleak
   ```

   `cat` lists the unreferenced objects found by the scan, if any.

4. To prove KASAN, boot again with the KUnit suites enabled and read the summary of the suite.
   Each `BUG: KASAN` report in the log is one of its deliberate faults.

   ```bash
   QEMU_KERNEL_PARAMS="log_buf_len=16M kunit.enable=1" nix run ~/.config/nixos#kernel-vm -- ~/src/kernel/build/<tree>-debug
   ```

   ```bash
   dmesg | grep '# kasan: pass'
   ```

   The line reports `fail:0` when every deliberate fault was caught.

## How to run kselftests in the VM

1. In the kernel shell, configure a selftests build: the VM configuration, the `config` fragments
   of the selected tests, then every module built in.

   ```bash
   mkdir -p ../build/<tree>-selftests
   cp ../build/<tree>-vm/.config ../build/<tree>-selftests/.config
   scripts/kconfig/merge_config.sh -m -O ../build/<tree>-selftests ../build/<tree>-selftests/.config tools/testing/selftests/sched_ext/config
   make O=../build/<tree>-selftests olddefconfig
   make O=../build/<tree>-selftests mod2yesconfig
   make O=../build/<tree>-selftests -j"$(nproc)"
   ```

2. Build and install the tests into the build directory.

   ```bash
   make O=../build/<tree>-selftests -j"$(nproc)" SKIP_TARGETS= TARGETS="<targets>" kselftest-install
   ```

   `<targets>` lists selftest directories, such as `sched_ext rtc`.

3. Run them in the VM with the script of this repository, which also walks the `pm_test` levels.
   The VM powers itself off when the script ends.

   ```bash
   nix run ~/.config/nixos#kernel-vm -- ~/src/kernel/build/<tree>-selftests ~/.config/nixos/kernel/run-selftests.sh
   ```

4. Read the results in the build directory.

   ```bash
   grep -E '^(ok|not ok)|# Totals' ~/src/kernel/build/<tree>-selftests/kselftest.log
   cat ~/src/kernel/build/<tree>-selftests/pm-test.log
   ```

## Reference

| Path | Content |
| --- | --- |
| `~/src/kernel/mainline` | Blobless clone of the mainline tree |
| `~/src/kernel/<remote>` | Worktree of a subsystem tree |
| `~/src/kernel/build/<tree>` | Out-of-tree build output, in the nested subvolume |
| `tools/kernel-shell.nix` | The `kernel` development shell |
| `home/mowsoon/dev/kernel.nix` | tmpfiles rule of the build subvolume |
| `~/src/kernel/build/<tree>-vm` | VM build: modules of the VM built in, all others disabled |
| `~/src/kernel/build/<tree>-debug` | VM build with the debug fragment |
| `~/src/kernel/build/vm` | Disk image of the `kernel-test` VM |
| `~/src/kernel/build/<tree>-selftests` | VM build with the selftest fragments, the installed tests and their logs |
| `~/src/kernel/build/vm/run` | Copy of the last script run by `kernel-vm` |
| `kernel/run-selftests.sh` | Runs the installed kselftests and the `pm_test` levels, results in the build directory |
| `kernel/debug.config` | Debug fragment: KASAN, lockdep, atomic sleep check, kmemleak and their self-tests |
| `hosts/kernel-test/default.nix` | VM booted on the build |
| `tools/kernel-vm.nix` | `kernel-vm` launcher |
| `tools/kernel-vm-modules.nix` | NixOS test that records the `lsmod` of the VM |

| Measure, 2026-11-01, mainline `7.4-rc1`, zen `7.2.9` configuration | Value |
| --- | --- |
| Blobless clone | 3.9 GiB of history, 1.8 GiB of working tree, about 45 min at 3 MiB/s |
| First full build, `-j32` | 1979 s, 7389 modules, no warning |
| Build output | 28 GiB in `~/src/kernel/build/mainline` |
| Rebuild after touching one driver | 27 to 36 s |
| VM build with `localyesconfig`, `-j32` | 290 s, no module, 4.6 GiB |
| VM boot on the VM build | `uname -r` gives `7.4.0-rc1`, the system is `running` with no failed unit |
| Debug build from the VM build | 398 s, then 111 s after a change of the fragment; 5.7 GiB |
| Debug boot | lockdep: all 395 testcases passed; kmemleak scan without unreferenced object |
| Selftests build, `sched_ext` and `bpf` fragments | Kernel 341 s; tests `sched_ext` and `rtc` in 70 s |
| Selftests run in the VM, 324 s | `rtc` 8 of 8; `sched_ext` 38 passed, 2 skipped (lazy preemption, `nohz_full`), 0 failed |
| `pm_test`, `freeze` and `disk` | `freezer` passes; `devices` and beyond fail on virtiofs (`-95`) |
| Debug boot with `kunit.enable=1` | `# kasan: pass:60 fail:0 skip:16 total:76`, 164 KASAN reports |
