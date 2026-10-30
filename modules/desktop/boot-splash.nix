{ config, lib, ... }:
let
  cfg = config.custom.bootSplash;
in
{
  options.custom.bootSplash = {
    enable = lib.mkEnableOption "the Plymouth boot splash and the palette and keymap of the console from the initrd on";
  };

  config = lib.mkIf cfg.enable {
    boot = {
      plymouth.enable = true;
      consoleLogLevel = 3;
      initrd.verbose = false;
      kernelParams = [
        "quiet"
        "rd.udev.log_level=3"
        "udev.log_priority=3"
      ];
    };

    console.earlySetup = true;

    stylix.targets = {
      plymouth.enable = true;
      console.enable = true;
    };
  };
}
