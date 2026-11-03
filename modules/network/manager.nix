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

    systemd.services = {
      NetworkManager.serviceConfig = {
        NoNewPrivileges = true;
        ProtectSystem = "full";
        ReadWritePaths = [ "/etc/NetworkManager/system-connections" ];
        ProtectKernelModules = true;
        ProtectHostname = true;
        RestrictNamespaces = true;
        LockPersonality = true;
        MemoryDenyWriteExecute = true;
        SystemCallArchitectures = "native";
        SystemCallFilter = [
          "@system-service"
          "bpf"
        ];
        SystemCallErrorNumber = "EPERM";
        RestrictAddressFamilies = [
          "AF_UNIX"
          "AF_NETLINK"
          "AF_PACKET"
          "AF_INET"
          "AF_INET6"
        ];
        CapabilityBoundingSet = [ "~CAP_SYS_MODULE CAP_SYS_CHROOT CAP_CHOWN" ];
      };

      NetworkManager-dispatcher.serviceConfig = {
        NoNewPrivileges = true;
        ProtectSystem = "strict";
        ReadWritePaths = [ "-/run/chrony" ];
        PrivateTmp = true;
        ProtectHome = true;
        PrivateDevices = true;
        PrivateNetwork = true;
        ProtectKernelTunables = true;
        ProtectKernelModules = true;
        ProtectKernelLogs = true;
        ProtectControlGroups = true;
        ProtectClock = true;
        ProtectHostname = true;
        RestrictNamespaces = true;
        RestrictRealtime = true;
        RestrictSUIDSGID = true;
        LockPersonality = true;
        MemoryDenyWriteExecute = true;
        SystemCallArchitectures = "native";
        SystemCallFilter = [ "@system-service" ];
        RestrictAddressFamilies = [ "AF_UNIX" ];
        CapabilityBoundingSet = [ "CAP_DAC_OVERRIDE" ];
        UMask = "0077";
      };

      iwd.serviceConfig = {
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
    };

    custom = {
      hardening.serviceExposure = {
        NetworkManager = "3.7";
        NetworkManager-dispatcher = "1.5";
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
