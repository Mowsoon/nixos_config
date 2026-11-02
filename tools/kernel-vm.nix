{ writeShellApplication, vm }:
writeShellApplication {
  name = "kernel-vm";
  text = ''
    build=$(realpath "''${1:?usage: kernel-vm <build directory> [script]}")
    export KERNEL_TREE="''${KERNEL_TREE:-$HOME/src/kernel}"
    tree=$(realpath "$KERNEL_TREE")
    state="$tree/build/vm"
    mkdir -p "$state"
    export NIX_DISK_IMAGE="$state/kernel-test.qcow2"
    export NIXPKGS_QEMU_KERNEL_kernel_test="$build/arch/x86/boot/bzImage"

    case "$build" in
      "$tree"/*) build_in_vm="/src/''${build#"$tree"/}" ;;
      *) echo "$build is outside $tree, which the VM cannot see" >&2; exit 1 ;;
    esac

    if [ -n "''${2:-}" ]; then
      install -m 755 "$2" "$state/run"
      QEMU_KERNEL_PARAMS="''${QEMU_KERNEL_PARAMS:-} systemd.setenv=KERNEL_BUILD=$build_in_vm systemd.run=/src/build/vm/run systemd.run_success_action=poweroff systemd.run_failure_action=poweroff"
      export QEMU_KERNEL_PARAMS
    fi

    exec ${vm}/bin/run-kernel-test-vm
  '';
}
