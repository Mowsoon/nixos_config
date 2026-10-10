{ config, lib, ... }:
let
  cfg = config.custom.asus;
in
{
  options.custom.asus = {
    enable = lib.mkEnableOption "the ASUS platform daemon for fans, profiles, keyboard backlight and charge limit";
  };

  config = lib.mkIf cfg.enable {
    services.asusd.enable = true;

    custom.persistence.directories = [ "/etc/asusd" ];
  };
}
