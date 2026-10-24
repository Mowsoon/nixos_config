{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.custom.rgb;
  inherit (cfg) effects;
  openrgb = config.services.hardware.openrgb;
  stateDirectory = "/var/lib/OpenRGB";
  receiverGroup = "openrgb-receiver";
  keysGroup = "rgb-keys";
  keyDevice = "/dev/input/g915x-keyboard";
  keySocket = "/run/rgb-keyreader.sock";
  openrgbWithoutUdevRules = pkgs.symlinkJoin {
    name = "openrgb-without-udev-rules-${pkgs.openrgb.version}";
    paths = [ pkgs.openrgb ];
    postBuild = "rm -r $out/lib/udev";
    meta.mainProgram = "openrgb";
  };
  rgbEffects = pkgs.callPackage ../../pkgs/rgb-effects/package.nix { };
  effectsConfig = pkgs.writeText "rgb-effects.json" (
    builtins.toJSON {
      server = {
        host = "127.0.0.1";
        inherit (openrgb.server) port;
      };
      inherit (effects)
        device
        schedule
        refreshSeconds
        windowColors
        fps
        batteryFps
        ;
      lowBattery = {
        inherit (effects.lowBattery) threshold brightness;
        model = effects.device;
      };
      ember = {
        inherit (effects.ember) colors durationMs brightness;
      };
      keySocket = if effects.keys.enable then keySocket else null;
    }
  );
  keyframe = lib.types.submodule {
    options = {
      time = lib.mkOption {
        type = lib.types.strMatching "([01][0-9]|2[0-3]):[0-5][0-9]";
        description = "Time of day, HH:MM, at which the keyframe is reached.";
      };
      color = lib.mkOption {
        type = lib.types.strMatching "#[0-9a-fA-F]{6}";
        description = "Background colour at that time, #rrggbb.";
      };
      brightness = lib.mkOption {
        type = lib.types.numbers.between 0 1;
        description = "Scale applied to the colour at that time, from 0 to 1.";
      };
    };
  };
in
{
  options.custom.rgb = {
    enable = lib.mkEnableOption "the OpenRGB SDK server, confined to the Logitech LIGHTSPEED receiver";

    effects = {
      enable = lib.mkEnableOption "the keyboard lighting effects daemon in the graphical session";

      user = lib.mkOption {
        type = lib.types.str;
        default = "mowsoon";
        description = "Only user whose graphical session starts the effects daemon.";
      };

      device = lib.mkOption {
        type = lib.types.str;
        default = "G915 X LS";
        description = "OpenRGB device name the effects are painted on.";
      };

      refreshSeconds = lib.mkOption {
        type = lib.types.ints.between 1 3600;
        default = 60;
        description = "Interval at which the time-of-day background is recomputed.";
      };

      fps = lib.mkOption {
        type = lib.types.ints.between 1 60;
        default = 30;
        description = "Frame rate while an animation runs; the daemon sends nothing while the keyboard is still.";
      };

      batteryFps = lib.mkOption {
        type = lib.types.ints.between 1 60;
        default = 15;
        description = "Frame rate of animations while the laptop runs on battery, reported by UPower.";
      };

      lowBattery = {
        threshold = lib.mkOption {
          type = lib.types.ints.between 1 100;
          default = 20;
          description = "Keyboard battery percentage at or below which the lighting brightness is capped.";
        };

        brightness = lib.mkOption {
          type = lib.types.numbers.between 0.05 1;
          default = 0.4;
          description = "Brightness ceiling, from 0 to 1, while the keyboard battery is low.";
        };
      };

      keys = {
        enable = lib.mkEnableOption "the confined key reader that feeds the key-reactive effects";

        mode = lib.mkOption {
          type = lib.types.enum [
            "position"
            "pulse"
          ];
          default = "position";
          description = "position sends which key was pressed; pulse sends only that a key was pressed.";
        };
      };

      ember = {
        colors = lib.mkOption {
          type = lib.types.nonEmptyListOf (lib.types.strMatching "#[0-9a-fA-F]{6}");
          default = [
            "#ffffff"
            "#fff1a8"
            "#ffb347"
            "#ff6a00"
            "#c42000"
            "#5a0a00"
          ];
          description = "Ember palette from hottest to coldest; a pressed key walks through it, then returns to the background.";
        };

        durationMs = lib.mkOption {
          type = lib.types.ints.between 50 10000;
          default = 900;
          description = "Time a pressed key takes to cool down to the background.";
        };

        brightness = lib.mkOption {
          type = lib.types.numbers.between 0 1;
          default = 0.8;
          description = "Scale applied to the ember palette, independent of the time-of-day brightness.";
        };
      };

      windowColors = lib.mkOption {
        type = lib.types.attrsOf (lib.types.strMatching "#[0-9a-fA-F]{6}");
        default = {
          "com.anthropic.Claude" = "#d97757";
          discord = "#5865f2";
          firefox = "#ff7139";
          "org.kde.konsole" = "#2ecc71";
          "org.kde.kwrite" = "#3daee9";
          spotify = "#1db954";
        };
        description = "Background hue per application identifier (KWin resource class); other applications keep the schedule colour. Brightness always follows the schedule.";
      };

      schedule = lib.mkOption {
        type = lib.types.nonEmptyListOf keyframe;
        default = [
          {
            time = "00:30";
            color = "#5a1a00";
            brightness = 0.12;
          }
          {
            time = "06:30";
            color = "#9fb8ff";
            brightness = 0.35;
          }
          {
            time = "09:00";
            color = "#e8f0ff";
            brightness = 0.6;
          }
          {
            time = "18:00";
            color = "#ffb070";
            brightness = 0.6;
          }
          {
            time = "22:00";
            color = "#ff6a2a";
            brightness = 0.3;
          }
        ];
        description = "Time-of-day background keyframes, sorted by time, interpolated in between.";
      };
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = !effects.enable || config.users.users ? ${effects.user};
        message = "custom.rgb.effects.user must name a declared user";
      }
    ];

    services = {
      hardware.openrgb = {
        enable = true;
        package = openrgbWithoutUdevRules;
        motherboard = null;
      };

      udev.extraRules = ''
        SUBSYSTEM=="hidraw", ATTRS{idVendor}=="046d", ATTRS{idProduct}=="c547", GROUP="${receiverGroup}", MODE="0660"
      ''
      + lib.optionalString (effects.enable && effects.keys.enable) ''
        SUBSYSTEM=="input", KERNEL=="event*", ATTRS{id/vendor}=="046d", ATTRS{id/product}=="40b5", GROUP="${keysGroup}", MODE="0640", SYMLINK+="input/g915x-keyboard"
      '';
    };

    users.groups = {
      ${receiverGroup} = { };
      ${keysGroup} = lib.mkIf (effects.enable && effects.keys.enable) { };
    };

    systemd = {
      sockets.rgb-keyreader = lib.mkIf (effects.enable && effects.keys.enable) {
        description = "Key reader socket of the keyboard lighting effects";
        wantedBy = [ "sockets.target" ];
        socketConfig = {
          ListenSequentialPacket = keySocket;
          SocketUser = effects.user;
          SocketMode = "0600";
          RemoveOnStop = true;
        };
      };

      services = {
        rgb-keyreader = lib.mkIf (effects.enable && effects.keys.enable) {
          description = "Key reader of the keyboard lighting effects";
          requires = [ "rgb-keyreader.socket" ];
          serviceConfig = {
            ExecStart = lib.escapeShellArgs [
              (lib.getExe' rgbEffects "rgb-keyreader")
              "--device"
              keyDevice
              "--mode"
              effects.keys.mode
            ];
            DynamicUser = true;
            SupplementaryGroups = [ keysGroup ];
            DevicePolicy = "closed";
            DeviceAllow = [ "char-input r" ];
            PrivateNetwork = true;
            IPAddressDeny = [ "any" ];
            RestrictAddressFamilies = [ "AF_UNIX" ];
            CapabilityBoundingSet = [ "" ];
            ProtectSystem = "strict";
            ProtectHome = true;
            PrivateTmp = true;
            ProtectClock = true;
            ProtectControlGroups = true;
            ProtectHostname = true;
            ProtectKernelLogs = true;
            ProtectKernelModules = true;
            ProtectKernelTunables = true;
            ProtectProc = "invisible";
            ProcSubset = "pid";
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
            LogLevelMax = "warning";
          };
        };

        openrgb.serviceConfig = {
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

      user.services.rgb-effects = lib.mkIf effects.enable {
        description = "Keyboard lighting effects";
        wantedBy = [ "graphical-session.target" ];
        partOf = [ "graphical-session.target" ];
        after = [ "graphical-session.target" ];
        unitConfig.ConditionUser = effects.user;
        serviceConfig = {
          ExecStart = "${lib.getExe rgbEffects} --config ${effectsConfig}";
          Restart = "on-failure";
          RestartSec = 5;
          RestrictAddressFamilies = [
            "AF_UNIX"
            "AF_INET"
          ];
          NoNewPrivileges = true;
          CapabilityBoundingSet = [ "" ];
          ProtectSystem = "strict";
          ProtectHome = "read-only";
          PrivateTmp = true;
          PrivateDevices = true;
          ProtectClock = true;
          ProtectControlGroups = true;
          ProtectHostname = true;
          ProtectKernelLogs = true;
          ProtectKernelModules = true;
          ProtectKernelTunables = true;
          ProtectProc = "invisible";
          RestrictSUIDSGID = true;
          MemoryDenyWriteExecute = true;
          LockPersonality = true;
          RestrictNamespaces = true;
          RestrictRealtime = true;
          SystemCallArchitectures = "native";
          SystemCallFilter = [ "@system-service" ];
          UMask = "0077";
        };
      };
    };
  };
}
