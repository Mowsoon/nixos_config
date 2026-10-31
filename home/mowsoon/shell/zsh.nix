{
  config,
  lib,
  pkgs,
  ...
}:
{
  home.packages = [ pkgs.zsh-completions ];

  programs.zsh = {
    enable = true;
    enableCompletion = true;
    completionInit = ''
      autoload -U compinit
      () {
        local dir=''${XDG_CACHE_HOME:-$HOME/.cache}/zsh
        local system=''${''${:-/run/current-system}:A:t}
        local home=''${''${:-$HOME/.local/state/home-manager/gcroots/current-home}:A:t}
        local dump=$dir/zcompdump-''${system[1,32]}-''${home[1,32]}
        if [[ -f $dump ]]; then
          compinit -C -d $dump
        else
          mkdir -p $dir
          rm -f $dir/zcompdump-*(N)
          compinit -d $dump
        fi
      }
    '';
    autosuggestion = {
      enable = true;
      strategy = [
        "match_prev_cmd"
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
      "INTERACTIVE_COMMENTS"
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
      ignoreDups = true;
      findNoDups = true;
    };

    historySubstringSearch = {
      enable = true;
      searchUpKey = [
        "^[[A"
        "^[OA"
      ];
      searchDownKey = [
        "^[[B"
        "^[OB"
      ];
    };

    initContent = lib.mkMerge [
      (lib.mkOrder 600 ''
        zstyle ':completion:*' matcher-list 'm:{a-z}={A-Za-z}'
        zstyle ':completion:*' list-colors ''${(s.:.)LS_COLORS}
        zstyle ':completion:*:descriptions' format '[%d]'
        zstyle ':completion:*' menu no
      '')
      ''
        export HISTORY_SUBSTRING_SEARCH_ENSURE_UNIQUE=1
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

        expand-dots() {
          if [[ $LBUFFER == (|*[[:space:]/]).. ]]; then
            LBUFFER+=/..
          else
            LBUFFER+=.
          fi
        }
        zle -N expand-dots
        bindkey . expand-dots
        bindkey -M isearch . self-insert

        autoload -Uz edit-command-line
        zle -N edit-command-line
        bindkey '^X^E' edit-command-line
      ''
      "ns() { NS_PACKAGES=\"$*\" IN_NIX_SHELL=impure nix shell \${@/#/nixpkgs#} }"
      (lib.mkOrder 1100 "ZSH_AUTOSUGGEST_STRATEGY=(${lib.concatStringsSep " " config.programs.zsh.autosuggestion.strategy})")
    ];
  };
}
