{
  config,
  lib,
  pkgs,
  ...
}:
let
  eza = lib.getExe config.programs.eza.package;
  ohMyZsh = "${pkgs.oh-my-zsh}/share/oh-my-zsh";
in
{
  programs.zsh = {
    plugins = [
      {
        name = "forgit";
        src = "${pkgs.zsh-forgit}/share/zsh/zsh-forgit";
      }
      {
        name = "you-should-use";
        src = "${pkgs.zsh-you-should-use}/share/zsh/plugins/you-should-use";
      }
      {
        name = "sudo";
        src = "${ohMyZsh}/plugins/sudo";
      }
      {
        name = "fancy-ctrl-z";
        src = "${ohMyZsh}/plugins/fancy-ctrl-z";
      }
      {
        name = "clipboard";
        src = "${ohMyZsh}/lib";
        file = "clipboard.zsh";
      }
      {
        name = "copypath";
        src = "${ohMyZsh}/plugins/copypath";
      }
      {
        name = "copyfile";
        src = "${ohMyZsh}/plugins/copyfile";
      }
      {
        name = "copybuffer";
        src = "${ohMyZsh}/plugins/copybuffer";
      }
      {
        name = "dirhistory";
        src = "${ohMyZsh}/plugins/dirhistory";
      }
    ];

    initContent = lib.mkOrder 600 ''
      zstyle ':fzf-tab:*' use-fzf-default-opts yes
      zstyle ':fzf-tab:*' switch-group '<' '>'
      zstyle ':fzf-tab:complete:(cd|z|__zoxide_z):*' fzf-preview '${eza} -1 --color=always --icons=always $realpath'
      source ${pkgs.zsh-fzf-tab}/share/fzf-tab/fzf-tab.plugin.zsh
    '';
  };
}
