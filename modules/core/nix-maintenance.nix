{ config, lib, ... }:
let
  cfg = config.custom.nixMaintenance;
in
{
  options.custom.nixMaintenance = {
    enable = lib.mkEnableOption "low-priority builds, store deduplication and generation-aware garbage collection";

    keepGenerations = lib.mkOption {
      type = lib.types.ints.positive;
      default = 10;
      description = "Number of system generations the garbage collection always keeps, whatever their age.";
    };
  };

  config = lib.mkIf cfg.enable {
    nix = {
      daemonCPUSchedPolicy = "batch";
      daemonIOSchedClass = "idle";
      optimise.automatic = true;
    };

    programs.nh = {
      enable = true;
      clean = {
        enable = true;
        extraArgs = "--keep ${toString cfg.keepGenerations} --keep-since 14d";
      };
    };
  };
}
