{
  imports = [
    ./shell.nix
    ./git.nix
    ./packages.nix
    ./editor/nixvim.nix
  ];

  home.stateVersion = "26.11";
}
