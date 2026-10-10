{ config, lib, ... }:
let
  cfg = config.custom.windowsVolume;
in
{
  options.custom.windowsVolume = {
    enable = lib.mkEnableOption "on-demand read-only access to the encrypted Windows volume";

    device = lib.mkOption {
      type = lib.types.str;
      example = "/dev/disk/by-partuuid/00000000-0000-0000-0000-000000000000";
      description = "Encrypted block device that holds the Windows volume.";
    };

    type = lib.mkOption {
      type = lib.types.enum [
        "bitlk"
        "luks"
      ];
      default = "bitlk";
      description = "Encryption format passed to crypttab.";
    };

    diskSerial = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      description = "Serial number of the Windows disk, hidden from udisks with all its partitions.";
    };

    mountPoint = lib.mkOption {
      type = lib.types.str;
      default = "/mnt/windows";
      description = "Mount point of the unlocked volume.";
    };
  };

  config = lib.mkIf cfg.enable {
    boot.supportedFilesystems.ntfs = true;

    environment.etc.crypttab.text = ''
      windows ${cfg.device} none ${cfg.type},noauto,read-only
    '';

    systemd.mounts = [
      {
        what = "/dev/mapper/windows";
        where = cfg.mountPoint;
        type = "ntfs";
        options = "ro,nosuid,nodev,noexec";
      }
    ];

    services.udev.extraRules = lib.optionalString (cfg.diskSerial != null) ''
      ENV{ID_SERIAL}=="*${cfg.diskSerial}*", ENV{UDISKS_IGNORE}="1"
    '';
  };
}
