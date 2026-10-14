{
  imports = [
    ./shell.nix
    ./git.nix
    ./packages.nix
    ./audio.nix
    ./desktop.nix
    ./editor/nixvim.nix
  ];

  home.stateVersion = "26.11";
}
