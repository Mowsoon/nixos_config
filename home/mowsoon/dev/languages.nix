{ pkgs, ... }:
{
  home = {
    packages = with pkgs; [
      go
      python3
    ];

    sessionPath = [ "$HOME/go/bin" ];
  };
}
