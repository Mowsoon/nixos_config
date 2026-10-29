{ inputs, pkgs, ... }:
{
  imports = [ inputs.home-manager.nixosModules.home-manager ];

  programs = {
    zsh = {
      enable = true;
      enableGlobalCompInit = false;
    };
    ssh.extraConfig = "SetEnv TERM=xterm-256color";
  };

  environment = {
    pathsToLink = [ "/share/zsh" ];
    systemPackages = [ pkgs.kitty.terminfo ];
  };

  users.users.mowsoon.shell = pkgs.zsh;

  custom.unfreePackages = [
    "discord"
    "discord-unwrapped"
    "spotify"
    "terraform"
    "unrar"
  ];

  home-manager = {
    useGlobalPkgs = true;
    useUserPackages = true;
    sharedModules = [
      inputs.nixvim.homeModules.nixvim
      inputs.plasma-manager.homeModules.plasma-manager
    ];
    users.mowsoon.imports = [ ../../home/mowsoon ];
  };
}
