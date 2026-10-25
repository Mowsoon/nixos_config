{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.custom.rgb;
  openrgb = config.services.hardware.openrgb;
  stateDirectory = "/var/lib/OpenRGB";
  receiverGroup = "openrgb-receiver";
  openrgbWithoutUdevRules = pkgs.symlinkJoin {
    name = "openrgb-without-udev-rules-${pkgs.openrgb.version}";
    paths = [ pkgs.openrgb ];
    postBuild = "rm -r $out/lib/udev";
    meta.mainProgram = "openrgb";
  };
in
{
  options.custom.rgb.enable = lib.mkEnableOption "the OpenRGB SDK server, confined to the Logitech LIGHTSPEED receiver";

  config = lib.mkIf cfg.enable {
    services = {
      hardware.openrgb = {
        enable = true;
        package = openrgbWithoutUdevRules;
        motherboard = null;
      };

      udev.extraRules = ''
        SUBSYSTEM=="hidraw", ATTRS{idVendor}=="046d", ATTRS{idProduct}=="c547", GROUP="${receiverGroup}", MODE="0660"
      '';
    };

    users.groups.${receiverGroup} = { };

    systemd.services.openrgb.serviceConfig = {
      ExecStart = lib.mkForce (
        lib.escapeShellArgs [
          (lib.getExe openrgb.package)
          "--server"
          "--server-host"
          "127.0.0.1"
          "--server-port"
          (toString openrgb.server.port)
          "--config"
          stateDirectory
        ]
      );
      DynamicUser = true;
      SupplementaryGroups = [ receiverGroup ];
      DevicePolicy = "closed";
      DeviceAllow = [ "char-hidraw rw" ];
      IPAddressAllow = [ "localhost" ];
      IPAddressDeny = [ "any" ];
      RestrictAddressFamilies = [
        "AF_UNIX"
        "AF_INET"
        "AF_NETLINK"
      ];
      CapabilityBoundingSet = [ "" ];
      ProtectSystem = "strict";
      ProtectHome = true;
      ProtectClock = true;
      ProtectControlGroups = true;
      ProtectHostname = true;
      ProtectKernelLogs = true;
      ProtectKernelModules = true;
      ProtectKernelTunables = true;
      ProtectProc = "invisible";
      LockPersonality = true;
      MemoryDenyWriteExecute = true;
      RestrictNamespaces = true;
      RestrictRealtime = true;
      SystemCallArchitectures = "native";
      SystemCallFilter = [
        "@system-service"
        "~@privileged"
        "~@resources"
      ];
      UMask = "0077";
    };
  };
}
