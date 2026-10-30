{
  config,
  lib,
  pkgs,
  ...
}:
let
  rebuild = action: "nixos-rebuild ${action} --flake ~/.config/nixos#hephaestus --elevate sudo";
  bat = lib.getExe config.programs.bat.package;
  eza = lib.getExe config.programs.eza.package;
  fd = lib.getExe pkgs.fd;
in
{
  home.packages = [ pkgs.zsh-completions ];

  programs = {
    zoxide.enable = true;
    fzf.enable = true;

    zsh = {
      enable = true;
      enableCompletion = true;
      autosuggestion = {
        enable = true;
        strategy = [
          "history"
          "completion"
        ];
      };
      syntaxHighlighting = {
        enable = true;
        highlighters = [ "brackets" ];
      };
      autocd = true;
      defaultKeymap = "emacs";

      setOptions = [
        "AUTO_PUSHD"
        "PUSHD_IGNORE_DUPS"
        "PUSHD_SILENT"
      ];

      dirHashes = {
        nixos = "$HOME/.config/nixos";
        private = "$HOME/.config/nixos-private";
      };

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
        ll = "eza -l";
        la = "eza -la";
        lt = "eza --tree --level=2";
        grep = "grep --color=auto";
        diff = "diff --color=auto";
        ip = "ip -color=auto";
        kubectl = "kubecolor";
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
          name = "forgit";
          src = "${pkgs.zsh-forgit}/share/zsh/zsh-forgit";
        }
        {
          name = "dirhistory";
          src = "${pkgs.oh-my-zsh}/share/oh-my-zsh/plugins/dirhistory";
        }
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
        (lib.mkOrder 600 ''
          zstyle ':completion:*' matcher-list 'm:{a-z}={A-Za-z}'
          zstyle ':completion:*' list-colors ''${(s.:.)LS_COLORS}
          zstyle ':completion:*:descriptions' format '[%d]'
          zstyle ':completion:*' menu no
          zstyle ':fzf-tab:*' use-fzf-default-opts yes
          zstyle ':fzf-tab:*' switch-group '<' '>'
          zstyle ':fzf-tab:complete:(cd|z|__zoxide_z):*' fzf-preview '${eza} -1 --color=always --icons=always $realpath'
          source ${pkgs.zsh-fzf-tab}/share/fzf-tab/fzf-tab.plugin.zsh
        '')
        "source ${./p10k.zsh}"
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
          WORDCHARS=''${WORDCHARS//\/}
          bindkey '^[[H' beginning-of-line
          bindkey '^[OH' beginning-of-line
          bindkey '^[[F' end-of-line
          bindkey '^[OF' end-of-line
          bindkey '^[[3~' delete-char
          bindkey '^[[1;5C' forward-word
          bindkey '^[[1;5D' backward-word
          bindkey '^H' backward-kill-word
          bindkey '^[[3;5~' kill-word
          bindkey '^[[Z' reverse-menu-complete
        ''
        "ns() { nix shell \${@/#/nixpkgs#} }"
      ];
    };
  };
}
