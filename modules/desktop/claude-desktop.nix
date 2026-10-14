{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.custom.claudeDesktop;
  package = pkgs.callPackage ../../pkgs/claude-desktop/package.nix { };
in
{
  options.custom.claudeDesktop = {
    enable = lib.mkEnableOption "the Claude desktop application with the Cowork virtual machine stack";
  };

  config = lib.mkIf cfg.enable {
    environment.systemPackages = [ package ];

    programs.nix-ld.enable = true;

    systemd.tmpfiles.settings.claude-desktop = {
      "/usr/share/OVMF/OVMF_CODE_4M.fd"."L+".argument = "${pkgs.OVMF.fd}/FV/OVMF_CODE.fd";
      "/usr/share/OVMF/OVMF_VARS_4M.fd"."L+".argument = "${pkgs.OVMF.fd}/FV/OVMF_VARS.fd";
      "/usr/bin/virtiofsd"."L+".argument = lib.getExe pkgs.virtiofsd;
    };

    custom = {
      unfreePackages = [ "claude-desktop" ];
      network.opensnitch = {
        allowedExecutables.claude-desktop = "${package}/lib/claude-desktop/claude-desktop";
        allowedExecutablePatterns.claude-code = "^/home/[^/]+/\\.config/Claude/claude-code/[0-9.]+/[0-9a-f]+/claude$";
      };
    };
  };
}
