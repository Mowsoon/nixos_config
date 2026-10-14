{
  writeShellApplication,
  OVMFFull,
  qemu_kvm,
  swtpm,
  iso,
}:
writeShellApplication {
  name = "rehearsal";
  runtimeInputs = [
    qemu_kvm
    swtpm
  ];
  text = ''
    state=rehearsal
    mkdir -p "$state/swtpm"

    if [ ! -f "$state/disk.qcow2" ]; then
      qemu-img create -f qcow2 "$state/disk.qcow2" 64G
    fi

    if [ ! -f "$state/efi-vars.fd" ]; then
      install -m 600 ${OVMFFull.fd}/FV/OVMF_VARS.fd "$state/efi-vars.fd"
    fi

    swtpm socket --tpm2 --daemon --terminate \
      --tpmstate dir="$state/swtpm" \
      --ctrl type=unixio,path="$state/swtpm/socket"

    iso_files=(${iso}/iso/*.iso)

    exec qemu-system-x86_64 \
      -machine q35,smm=on,accel=kvm \
      -cpu host \
      -smp 4 \
      -m 8192 \
      -global driver=cfi.pflash01,property=secure,value=on \
      -drive if=pflash,format=raw,unit=0,readonly=on,file=${OVMFFull.fd}/FV/OVMF_CODE.fd \
      -drive if=pflash,format=raw,unit=1,file="$state/efi-vars.fd" \
      -chardev socket,id=chrtpm,path="$state/swtpm/socket" \
      -tpmdev emulator,id=tpm0,chardev=chrtpm \
      -device tpm-tis,tpmdev=tpm0 \
      -drive if=none,id=nvme0,file="$state/disk.qcow2",format=qcow2 \
      -device nvme,drive=nvme0,serial=rehearsal \
      -cdrom "''${iso_files[0]}" \
      -boot menu=on \
      -nic user,model=virtio-net-pci \
      -device virtio-vga \
      -display gtk \
      "$@"
  '';
}
