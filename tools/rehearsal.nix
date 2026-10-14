{
  writeShellApplication,
  OVMFFull,
  age,
  dosfstools,
  git,
  gnutar,
  mtools,
  openssh,
  openssl,
  qemu_kvm,
  swtpm,
  util-linux,
  zstd,
  iso,
}:
writeShellApplication {
  name = "rehearsal";
  runtimeInputs = [
    age
    dosfstools
    git
    gnutar
    mtools
    openssh
    openssl
    qemu_kvm
    swtpm
    util-linux
    zstd
  ];
  text = ''
    state=rehearsal
    repo=$(git rev-parse --show-toplevel)

    make_test_key() {
      local dir=$1 name=$2
      mkdir -p "$dir"
      openssl req -new -x509 -newkey rsa:4096 -nodes -days 3650 \
        -subj "/CN=Rehearsal $name/" \
        -keyout "$dir/$name.key" -out "$dir/$name.pem" 2>/dev/null
    }

    make_test_archive() {
      local stage
      stage=$(mktemp -d)

      mkdir -p "$stage/var/lib/sbctl/keys"
      uuidgen > "$stage/var/lib/sbctl/GUID"
      for key in PK KEK db; do
        make_test_key "$stage/var/lib/sbctl/keys/$key" "$key"
      done

      mkdir -p "$stage/etc/cryptsetup-keys.d"
      head -c 64 /dev/urandom > "$stage/etc/cryptsetup-keys.d/windows_data.key"

      mkdir -p "$stage/etc/NetworkManager/system-connections"
      printf '[connection]\nid=rehearsal-wired\ntype=ethernet\n' \
        > "$stage/etc/NetworkManager/system-connections/rehearsal-wired.nmconnection"

      mkdir -p "$stage/home/$USER/.ssh" "$stage/home/$USER/.config/nixos"
      ssh-keygen -q -t ed25519 -N "" -C rehearsal -f "$stage/home/$USER/.ssh/id_ed25519"
      git -C "$repo" archive HEAD | tar -x -C "$stage/home/$USER/.config/nixos"

      echo "Choose a test passphrase for the rehearsal archive."
      tar --create --zstd --xattrs --acls --file=- -C "$stage" var etc home \
        | age --passphrase --output "$state/arch-backup-rehearsal.tar.zst.age"

      mkfs.vfat -C -n "T7 Touch" "$state/t7.img" 65536 > /dev/null
      mcopy -i "$state/t7.img" "$state/arch-backup-rehearsal.tar.zst.age" ::/
      rm "$state/arch-backup-rehearsal.tar.zst.age"
      rm -rf "$stage"
    }

    mkdir -p "$state/swtpm"

    if [ ! -f "$state/disk.qcow2" ]; then
      qemu-img create -f qcow2 "$state/disk.qcow2" 64G
    fi

    if [ ! -f "$state/efi-vars.fd" ]; then
      install -m 600 ${OVMFFull.fd}/FV/OVMF_VARS.fd "$state/efi-vars.fd"
    fi

    if [ ! -f "$state/t7.img" ]; then
      make_test_archive
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
      -device qemu-xhci \
      -drive if=none,id=t7,file="$state/t7.img",format=raw \
      -device usb-storage,drive=t7 \
      -cdrom "''${iso_files[0]}" \
      -boot menu=on \
      -nic user,model=virtio-net-pci \
      -device virtio-vga \
      -display gtk \
      "$@"
  '';
}
