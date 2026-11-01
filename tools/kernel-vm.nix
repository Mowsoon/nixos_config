{ writeShellApplication, vm }:
writeShellApplication {
  name = "kernel-vm";
  text = ''
    build=$(realpath "''${1:?usage: kernel-vm <build directory>}")
    export KERNEL_TREE="''${KERNEL_TREE:-$HOME/src/kernel}"
    state="$KERNEL_TREE/build/vm"
    mkdir -p "$state"
    export NIX_DISK_IMAGE="$state/kernel-test.qcow2"
    export NIXPKGS_QEMU_KERNEL_kernel_test="$build/arch/x86/boot/bzImage"
    exec ${vm}/bin/run-kernel-test-vm
  '';
}
