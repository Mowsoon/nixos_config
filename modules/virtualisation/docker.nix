{ config, lib, ... }:
let
  cfg = config.custom.docker;
in
{
  options.custom.docker = {
    enable = lib.mkEnableOption "the Docker daemon, started on first use";
  };

  config = lib.mkIf cfg.enable {
    virtualisation.docker = {
      enable = true;
      enableOnBoot = false;
      autoPrune = {
        enable = true;
        dates = "weekly";
        flags = [ "--all" ];
      };
    };

    hardware.nvidia-container-toolkit.enable = config.custom.nvidia.enable;

    custom.network.opensnitch.allowedExecutablePatterns.dockerd =
      "^/nix/store/[a-z0-9]{32}-moby-[^/]+/libexec/docker/(dockerd|docker-proxy)$";
  };
}
