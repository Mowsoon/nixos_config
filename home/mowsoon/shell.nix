{ lib, pkgs, ... }:
{
  programs.zsh = {
    enable = true;
    enableCompletion = true;
    autosuggestion.enable = true;
    syntaxHighlighting.enable = true;

    history = {
      size = 10000;
      save = 20000;
      append = true;
      share = true;
      ignoreAllDups = true;
    };

    shellAliases = {
      sudo = "sudo ";
      rm = "rm -I --preserve-root";
      cp = "cp -i";
      mv = "mv -i";
      ll = "ls -l";
      la = "ls -la";
      grep = "grep --color=auto";
      k = "kubectl";
      f = "flux";
      cctl = "clusterctl";
      tf = "terraform";
    };

    plugins = [
      {
        name = "powerlevel10k";
        src = pkgs.zsh-powerlevel10k;
        file = "share/zsh-powerlevel10k/powerlevel10k.zsh-theme";
      }
    ];

    initContent = lib.mkMerge [
      (lib.mkOrder 500 ''
        if [[ -r "''${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-''${(%):-%n}.zsh" ]]; then
          source "''${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-''${(%):-%n}.zsh"
        fi
      '')
      "source ${./p10k.zsh}"
    ];
  };
}
