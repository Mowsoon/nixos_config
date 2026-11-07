{
  writeShellApplication,
  coreutils,
  vm,
}:
writeShellApplication {
  name = "kernel-hibernate-vm";
  runtimeInputs = [ coreutils ];
  text = ''
    usage="usage: kernel-hibernate-vm <build directory> <hibernate|check|pcr>"
    build=$(realpath "''${1:?$usage}")
    step=''${2:?$usage}
    state="$(realpath "''${KERNEL_TREE:-$HOME/src/kernel}")/build/vm-hibernate"
    mkdir -p "$state"

    export NIX_DISK_IMAGE="$state/root.qcow2"
    export NIX_SWTPM_DIR="$state/swtpm"
    export KERNEL_HIBERNATE_SWAP="$state/swap.img"
    if [ ! -e "$KERNEL_HIBERNATE_SWAP" ]; then
      truncate -s 4G "$KERNEL_HIBERNATE_SWAP"
    fi

    export NIXPKGS_QEMU_KERNEL_kernel_hibernate="$build/arch/x86/boot/bzImage"
    QEMU_KERNEL_PARAMS="''${QEMU_KERNEL_PARAMS:-} hibernation_test=$step resume=/dev/disk/by-id/virtio-hibernate-swap"
    export QEMU_KERNEL_PARAMS

    exec ${vm}/bin/run-kernel-hibernate-vm
  '';
}
