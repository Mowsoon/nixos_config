{ lib, ... }:
{
  disko.devices.disk.main.device = lib.mkForce "/dev/disk/by-id/nvme-QEMU_NVMe_Ctrl_rehearsal";
}
