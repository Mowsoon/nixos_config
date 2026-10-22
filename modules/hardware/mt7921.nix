{ config, lib, ... }:
let
  cfg = config.custom.mt7921;
in
{
  options.custom.mt7921 = {
    enable = lib.mkEnableOption "the mt76 Wi-Fi drivers rebuilt with the MT7921 hibernation restore fix";
  };

  config = lib.mkIf cfg.enable {
    boot.extraModulePackages = [
      (config.boot.kernelPackages.callPackage ../../pkgs/mt76/package.nix { })
    ];
  };
}
