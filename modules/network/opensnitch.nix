{ config, lib, ... }:
let
  cfg = config.custom.network.opensnitch;

  allowRule =
    {
      name,
      operand,
      data,
      type ? "simple",
      precedence ? false,
    }:
    lib.nameValuePair name {
      inherit name precedence;
      enabled = true;
      action = "allow";
      duration = "always";
      operator = {
        inherit operand data type;
        sensitive = false;
      };
    };

  loopbackRules = [
    (allowRule {
      name = "000-allow-loopback";
      operand = "dest.network";
      data = "127.0.0.0/8";
      type = "network";
      precedence = true;
    })
    (allowRule {
      name = "000-allow-loopback6";
      operand = "dest.ip";
      data = "::1";
      precedence = true;
    })
  ];

  executableRules = lib.mapAttrsToList (
    name: data:
    allowRule {
      name = "allow-${name}";
      operand = "process.path";
      inherit data;
    }
  ) cfg.allowedExecutables;
in
{
  options.custom.network.opensnitch = {
    enable = lib.mkEnableOption "the OpenSnitch outbound firewall with a deny-by-default policy";

    allowedExecutables = lib.mkOption {
      type = lib.types.attrsOf lib.types.str;
      default = { };
      description = "Executables allowed to open outbound connections, contributed by the modules that own them.";
    };
  };

  config = lib.mkIf cfg.enable {
    services.opensnitch = {
      enable = true;
      settings = {
        DefaultAction = "deny";
        DefaultDuration = "once";
        InterceptUnknown = false;
      };
      rules = lib.listToAttrs (loopbackRules ++ executableRules);
    };

    custom = {
      network.opensnitch.allowedExecutables = {
        nix = lib.getExe config.nix.package;
      }
      // lib.optionalAttrs config.services.timesyncd.enable {
        systemd-timesyncd = "${config.systemd.package}/lib/systemd/systemd-timesyncd";
      };
      persistence.directories = [ "/var/lib/opensnitch" ];
    };
  };
}
