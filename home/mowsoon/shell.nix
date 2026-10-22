{ lib, pkgs, ... }:
let
  rebuild = action: "nixos-rebuild ${action} --flake ~/.config/nixos#hephaestus --elevate sudo";
in
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

      nrs = rebuild "switch";
      nrt = rebuild "test";
      nrb = rebuild "boot";
      nrbr = "${rebuild "boot"} && systemctl reboot";
      nrr = "sudo nixos-rebuild switch --rollback";
      nkern = "readlink /run/booted-system/kernel /run/current-system/kernel";
      cdn = "cd ~/.config/nixos";

      hib = "systemctl hibernate";
      sus = "systemctl suspend";
      sush = "systemctl suspend-then-hibernate";

      jb = "journalctl -b";
      jbu = "journalctl -b --no-pager -u";
      jke = "journalctl -k -p err";

      gst = "git status";
      gaa = "git add -A";
      gcm = "git commit -m";
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
      "ns() { nix shell \${@/#/nixpkgs#} }"
    ];
  };
}
