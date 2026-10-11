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
    device = "/dev/disk/by-id/nvme-Samsung_SSD_990_PRO_1TB_<system-disk-serial>";
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
                "@persist/.snapshots" = { };
                "@log" = mkSubvolume "/var/log";
                "@home" = mkSubvolume "/home";
                "@home/.snapshots" = { };
                "@docker" = mkSubvolume "/var/lib/docker";
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
