let
  btrfsOptions = [
    "compress=zstd:3"
    "noatime"
  ];
  mkSubvolume = mountpoint: {
    inherit mountpoint;
    mountOptions = btrfsOptions;
  };
in
{
  disko.devices.disk.main = {
    type = "disk";
    device = "/dev/disk/by-id/nvme-Samsung_SSD_990_PRO_1TB_S7HDNS0YB64470V";
    content = {
      type = "gpt";
      partitions = {
        ESP = {
          size = "4G";
          type = "EF00";
          content = {
            type = "filesystem";
            format = "vfat";
            mountpoint = "/boot";
            mountOptions = [ "umask=0077" ];
          };
        };

        luks = {
          size = "100%";
          content = {
            type = "luks";
            name = "cryptroot";
            extraFormatArgs = [
              "--sector-size"
              "4096"
            ];
            settings = {
              allowDiscards = true;
              bypassWorkqueues = true;
            };
            content = {
              type = "btrfs";
              extraArgs = [ "-f" ];
              subvolumes = {
                "@root" = mkSubvolume "/";
                "@nix" = mkSubvolume "/nix";
                "@persist" = mkSubvolume "/persist";
                "@log" = mkSubvolume "/var/log";
                "@home" = mkSubvolume "/home";
                "@swap" = {
                  mountpoint = "/swap";
                  mountOptions = [ "noatime" ];
                  swap.swapfile = {
                    size = "32G";
                    priority = 0;
                  };
                };
              };
            };
          };
        };
      };
    };
  };
}
