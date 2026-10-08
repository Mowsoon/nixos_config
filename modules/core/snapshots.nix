{ config, lib, ... }:
let
  cfg = config.custom.snapshots;
  timeline = subvolume: {
    SUBVOLUME = subvolume;
    TIMELINE_CREATE = true;
    TIMELINE_CLEANUP = true;
    TIMELINE_LIMIT_HOURLY = 24;
    TIMELINE_LIMIT_DAILY = 7;
    TIMELINE_LIMIT_WEEKLY = 4;
    TIMELINE_LIMIT_MONTHLY = 0;
    TIMELINE_LIMIT_QUARTERLY = 0;
    TIMELINE_LIMIT_YEARLY = 0;
  };
in
{
  options.custom.snapshots = {
    enable = lib.mkEnableOption "hourly snapper timelines on the persistent subvolumes";

    subvolumes = lib.mkOption {
      type = lib.types.attrsOf lib.types.str;
      example = {
        home = "/home";
      };
      description = "Snapper configuration names mapped to the mount point they protect.";
    };
  };

  config = lib.mkIf cfg.enable {
    services.snapper.configs = lib.mapAttrs (_: timeline) cfg.subvolumes;
  };
}
