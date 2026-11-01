{ lib, pkgs, ... }:
{
  disko = {
    tests.efi = true;
    imageBuilder = {
      copyNixStore = lib.mkForce true;
      pkgs = pkgs.extend (
        _: prev: {
          vmTools = prev.vmTools.override {
            kernelImage = prev.linux.target;
          };
        }
      );
    };
    devices.disk.main.content.partitions.luks.content.content.subvolumes."@swap".swap.swapfile.size =
      lib.mkForce "1G";
  };

  boot = {
    kernelParams = [
      "console=tty0"
      "console=ttyS0,115200n8"
    ];
    initrd.systemd.emergencyAccess = true;
    lanzaboote = {
      autoGenerateKeys.enable = true;
      autoEnrollKeys = {
        enable = true;
        autoReboot = true;
      };
    };
  };

  systemd.services.generate-sb-keys.unitConfig.RequiresMountsFor = [ "/var/lib/sbctl" ];

  virtualisation = {
    tpm.enable = true;
    useBootLoader = true;
    useEFIBoot = true;
    bootPartition = null;
    efi.keepVariables = false;
    writableStore = false;
    sharedDirectories = lib.mkForce { };
    fileSystems = import ./early-mounts.nix lib;
  };
}
