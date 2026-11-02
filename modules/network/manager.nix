{ config, lib, ... }:
let
  cfg = config.custom.network.manager;
in
{
  options.custom.network.manager = {
    enable = lib.mkEnableOption "NetworkManager with the iwd Wi-Fi backend";
  };

  config = lib.mkIf cfg.enable {
    networking = {
      networkmanager = {
        enable = true;
        wifi.backend = "iwd";
      };
      wireless.iwd.settings.General.AddressRandomization = "network";
    };

    systemd.services.iwd.serviceConfig = {
      ProtectClock = true;
      ProtectHostname = true;
      ProtectKernelLogs = true;
      ProtectProc = "invisible";
      RestrictNamespaces = true;
      RestrictRealtime = true;
      RestrictSUIDSGID = true;
      LockPersonality = true;
      MemoryDenyWriteExecute = true;
      SystemCallArchitectures = "native";
      SystemCallFilter = [ "@system-service" ];
      RestrictAddressFamilies = [
        "AF_UNIX"
        "AF_NETLINK"
        "AF_PACKET"
        "AF_INET"
        "AF_INET6"
        "AF_ALG"
      ];
      UMask = "0077";
    };

    custom = {
      hardening.serviceExposure = {
        NetworkManager = "6.8";
        NetworkManager-dispatcher = "9.4";
        iwd = "2.9";
      };
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
