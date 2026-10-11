{ inputs, pkgs, ... }:
{
  imports = [ inputs.home-manager.nixosModules.home-manager ];

  programs.zsh = {
    enable = true;
    enableGlobalCompInit = false;
  };

  environment.pathsToLink = [ "/share/zsh" ];

  users.users.mowsoon.shell = pkgs.zsh;

  home-manager = {
    useGlobalPkgs = true;
    useUserPackages = true;
    sharedModules = [ inputs.nixvim.homeModules.nixvim ];
    users.mowsoon.imports = [ ../../home/mowsoon ];
  };
}
