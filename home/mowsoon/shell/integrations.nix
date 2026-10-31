{
  config,
  lib,
  pkgs,
  ...
}:
let
  bat = lib.getExe config.programs.bat.package;
  eza = lib.getExe config.programs.eza.package;
  fd = lib.getExe pkgs.fd;
in
{
  programs = {
    zoxide.enable = true;
    nix-index.enable = true;
    nix-index-database.comma.enable = true;
    fzf = {
      enable = true;
      historyWidget.command = "";
    };

    atuin = {
      enable = true;
      flags = [ "--disable-up-arrow" ];
      forceOverwriteSettings = true;
      settings = {
        auto_sync = false;
        update_check = false;
        enter_accept = false;
        workspaces = true;
      };
    };

    bat = {
      enable = true;
      config.theme = "base16";
    };

    eza = {
      enable = true;
      enableZshIntegration = false;
      icons = "auto";
      git = true;
    };

    tealdeer = {
      enable = true;
      settings.updates = {
        auto_update = true;
        auto_update_interval_hours = 168;
      };
    };

    zsh.initContent = lib.mkMerge [
      ''
        export FZF_DEFAULT_COMMAND="${fd} --type f --hidden --exclude .git"
        export FZF_DEFAULT_OPTS="--height=80% --layout=reverse --border --color=fg:-1,bg:-1,bg+:0,gutter:-1,hl:6,hl+:14,info:3,prompt:6,pointer:6,marker:2,spinner:5,header:4,border:8"
        export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
        export FZF_CTRL_T_OPTS="--preview '${bat} --color=always --style=numbers --line-range=:200 {}'"
        export FZF_ALT_C_COMMAND="${fd} --type d --hidden --exclude .git"
        export FZF_ALT_C_OPTS="--preview '${eza} --tree --level=2 --color=always --icons=always {}'"
      ''
      ''
        export MANPAGER="sh -c 'col -bx | ${bat} -l man -p'"
        export MANROFFOPT=-c
      ''
    ];
  };
}
