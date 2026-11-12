{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.custom.nvidia;
  driver = config.hardware.nvidia.package.out;
in
{
  options.custom.nvidia = {
    enable = lib.mkEnableOption "the NVIDIA driver with open kernel modules on the discrete GPU";
  };

  config = lib.mkIf cfg.enable {
    custom = {
      unfreePackages = [
        "nvidia-x11"
        "nvidia-settings"
      ];
      hardening.serviceExposure = {
        nvidia-powerd = "1.8";
      };
    };

    boot.kernelModules = [ "msr" ];

    services = {
      xserver.videoDrivers = [ "nvidia" ];
      acpid.enable = lib.mkForce false;
    };

    hardware = {
      graphics = {
        enable = true;
        enable32Bit = true;
        extraPackages = [ pkgs.nvidia-vaapi-driver ];
      };

      nvidia = {
        open = true;
        package = config.boot.kernelPackages.nvidiaPackages.stable;
        modesetting.enable = true;
        powerManagement = {
          enable = true;
          kernelSuspendNotifier = false;
        };
        dynamicBoost.enable = true;
        moduleParams.nvidia = {
          NVreg_EnableS0ixPowerManagement = 1;
          NVreg_DynamicPowerManagement = 0;
        };
      };
    };

    systemd.services = {
      nvidia-powerd.serviceConfig = {
        NoNewPrivileges = true;
        ProtectSystem = "strict";
        ReadWritePaths = [
          "/run"
          "/sys/devices/system/cpu"
        ];
        ProtectHome = true;
        PrivateTmp = true;
        PrivateNetwork = true;
        DevicePolicy = "closed";
        DeviceAllow = [
          "char-nvidia rw"
          "char-nvidia-caps r"
          "char-cpu/msr rw"
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
        SystemCallErrorNumber = "EPERM";
        RestrictAddressFamilies = [
          "AF_UNIX"
          "AF_NETLINK"
        ];
        CapabilityBoundingSet = [
          "CAP_SYS_ADMIN"
          "CAP_SYS_RAWIO"
        ];
        UMask = "0077";
      };
    };

    environment = {
      etc."systemd/system-sleep/nvidia".source = pkgs.writeShellScript "nvidia-system-sleep" ''
        export PATH=${
          lib.makeBinPath [
            pkgs.coreutils
            pkgs.kbd
          ]
        }
        exec ${driver}/lib/systemd/system-sleep/nvidia "$@"
      '';

      sessionVariables = {
        LIBVA_DRIVER_NAME = "nvidia";
        NVD_BACKEND = "direct";
      };
    };

    programs.firefox.preferences."media.hardware-video-decoding.force-enabled" = true;
  };
}
