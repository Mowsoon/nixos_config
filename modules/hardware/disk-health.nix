{ config, lib, ... }:
let
  cfg = config.custom.diskHealth;
in
{
  options.custom.diskHealth = {
    enable = lib.mkEnableOption "SMART monitoring of every detected disk with desktop notifications";
  };

  config = lib.mkIf cfg.enable {
    custom.hardening.serviceExposure.smartd = "1.9";

    services.smartd = {
      enable = true;
      autodetect = true;
      notifications.systembus-notify.enable = true;
    };

    systemd.services.smartd.serviceConfig = {
      NoNewPrivileges = true;
      ProtectSystem = "strict";
      ProtectHome = true;
      PrivateTmp = true;
      PrivateNetwork = true;
      DevicePolicy = "closed";
      DeviceAllow = [
        "char-nvme r"
        "block-sd rw"
        "char-pts w"
        "char-tty w"
      ];
      ProtectKernelTunables = true;
      ProtectKernelModules = true;
      ProtectKernelLogs = true;
      ProtectControlGroups = true;
      ProtectClock = true;
      ProtectHostname = true;
      ProtectProc = "invisible";
      RestrictNamespaces = true;
      RestrictRealtime = true;
      RestrictSUIDSGID = true;
      LockPersonality = true;
      MemoryDenyWriteExecute = true;
      SystemCallArchitectures = "native";
      SystemCallFilter = [ "@system-service" ];
      RestrictAddressFamilies = [ "AF_UNIX" ];
      CapabilityBoundingSet = [
        "CAP_SYS_ADMIN"
        "CAP_SYS_RAWIO"
        "CAP_DAC_OVERRIDE"
      ];
      UMask = "0077";
    };
  };
}
