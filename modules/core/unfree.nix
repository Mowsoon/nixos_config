{ config, lib, ... }:
{
  options.custom.unfreePackages = lib.mkOption {
    type = lib.types.listOf lib.types.str;
    default = [ ];
    description = "Names of the unfree packages allowed to build, contributed by the modules that need them.";
  };

  config.nixpkgs.config.allowUnfreePredicate =
    pkg: builtins.elem (lib.getName pkg) config.custom.unfreePackages;
}
