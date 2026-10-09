{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.custom.secureBoot;
in
{
  options.custom.secureBoot = {
    enable = lib.mkEnableOption "Secure Boot signing of the boot chain with lanzaboote";

    pkiBundle = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/sbctl";
      description = "Directory holding the Secure Boot keys already enrolled in the firmware.";
    };
  };

  config = lib.mkIf cfg.enable {
    boot.lanzaboote = {
      enable = true;
      inherit (cfg) pkiBundle;
      configurationLimit = 10;
    };

    custom.persistence.directories = [ cfg.pkiBundle ];

    environment.systemPackages = [ pkgs.sbctl ];
  };
}
