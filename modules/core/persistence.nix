{ config, lib, ... }:
let
  cfg = config.custom.persistence;
in
{
  options.custom.persistence = {
    enable = lib.mkEnableOption "the persistence of declared state across root rollbacks";

    root = lib.mkOption {
      type = lib.types.str;
      example = "/persist";
      description = "Mount point of the persistent subvolume that holds the state.";
    };
  };

  config = lib.mkIf cfg.enable {
    environment.persistence.${cfg.root} = {
      hideMounts = true;
      directories = [
        "/var/lib/nixos"
        "/var/lib/systemd"
      ];
      files = [ "/etc/machine-id" ];
    };
  };
}
