{
  imports = [
    ./shell.nix
    ./terminal.nix
    ./git.nix
    ./packages.nix
    ./audio.nix
    ./desktop.nix
    ./mime.nix
    ./shortcuts.nix
    ./editor/nixvim.nix
  ];

  home.stateVersion = "26.11";
}
