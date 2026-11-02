{ config, lib, ... }:
let
  cfg = config.custom.fhsCompat;
in
{
  options.custom.fhsCompat = {
    enable = lib.mkEnableOption "/bin and /usr/bin entries resolved from the PATH of the caller, for scripts with FHS shebangs";
  };

  config = lib.mkIf cfg.enable {
    services.envfs.enable = true;
  };
}
