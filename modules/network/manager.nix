{ config, lib, ... }:
let
  cfg = config.custom.network.manager;
in
{
  options.custom.network.manager = {
    enable = lib.mkEnableOption "NetworkManager with the iwd Wi-Fi backend";
  };

  config = lib.mkIf cfg.enable {
    networking.networkmanager = {
      enable = true;
      wifi.backend = "iwd";
    };

    custom = {
      network.opensnitch.allowedExecutables.NetworkManager = "${config.networking.networkmanager.package}/bin/NetworkManager";
      persistence.directories = [
        {
          directory = "/etc/NetworkManager/system-connections";
          mode = "0700";
        }
        "/var/lib/NetworkManager"
        {
          directory = "/var/lib/iwd";
          mode = "0700";
        }
      ];
    };
  };
}
