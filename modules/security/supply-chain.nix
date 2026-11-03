{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.custom.supplyChain;
  notify = "${pkgs.libnotify}/bin/notify-send --app-name='Supply chain' --icon=security-medium";
  interval = toString (7 * 24 * 60 * 60);
in
{
  options.custom.supplyChain = {
    enable = lib.mkEnableOption "a vulnerability scan of the running system once a week, at the first hour on mains power with a network connection, reported by a desktop notification";

    alertScore = lib.mkOption {
      type = lib.types.strMatching "[0-9]+\\.[0-9]";
      default = "9.0";
      description = "Lowest CVSS score of the vulnerabilities that the diff of two closures and the summary of a scan single out.";
    };

    package = lib.mkOption {
      type = lib.types.package;
      readOnly = true;
      default = pkgs.callPackage ../../tools/supply-chain {
        nix = config.nix.package;
        host = config.networking.hostName;
        inherit (cfg) alertScore;
      };
      description = "The `supply-chain` application, built against the Nix and the host name of this system.";
    };
  };

  config = lib.mkIf cfg.enable {
    custom.network.opensnitch.allowedExecutables.grype = "${pkgs.grype}/bin/grype";

    systemd.user = {
      services.supply-chain-scan = {
        description = "Vulnerability scan of the running system";
        unitConfig = {
          ConditionUser = "!@system";
          ConditionACPower = true;
        };
        serviceConfig = {
          Type = "oneshot";
          Nice = 19;
          IOSchedulingClass = "idle";
        };
        script = ''
          stamp="''${XDG_STATE_HOME:-$HOME/.local/state}/supply-chain/last-scan"
          if [ -e "$stamp" ] && [ $(($(date +%s) - $(stat -c %Y "$stamp"))) -lt ${interval} ]; then
            exit 0
          fi
          if ! ${config.networking.networkmanager.package}/bin/nm-online --quiet --timeout=10; then
            echo "no network connection, next check in an hour"
            exit 0
          fi
          if ${lib.getExe cfg.package} scan > /dev/null; then
            mkdir -p "$(dirname "$stamp")"
            touch "$stamp"
            ${notify} "Supply chain scan" "$(${lib.getExe cfg.package} summary)"
          else
            ${notify} --urgency=critical "Supply chain scan failed" "journalctl --user -u supply-chain-scan"
            exit 1
          fi
        '';
      };

      timers.supply-chain-scan = {
        wantedBy = [ "timers.target" ];
        timerConfig = {
          OnCalendar = "hourly";
          Persistent = true;
        };
      };
    };
  };
}
