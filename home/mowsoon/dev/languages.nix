{ pkgs, ... }:
{
  home = {
    packages = with pkgs; [
      cargo
      clippy
      go
      python3
      rustc
      rustfmt
    ];

    sessionPath = [
      "$HOME/go/bin"
      "$HOME/.cargo/bin"
    ];
  };
}
