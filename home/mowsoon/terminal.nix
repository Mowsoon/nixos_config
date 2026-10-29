{ pkgs, ... }:
let
  palette = {
    background = "#0e1719";
    surface = "#18272a";
    selection = "#1f3a3d";
    foreground = "#d5e2df";
    accent = "#5fb3a8";
  };
in
{
  programs = {
    kitty = {
      enable = true;
      font = {
        package = pkgs.maple-mono.NF;
        name = "Maple Mono NF";
        size = 10.5;
      };
      settings = {
        disable_ligatures = "cursor";
        scrollback_lines = 10000;
        enable_audio_bell = false;
        update_check_interval = 0;
        window_padding_width = 6;
        background_opacity = "0.92";
        background_blur = 1;
        tab_bar_edge = "top";
        tab_bar_style = "powerline";

        inherit (palette) foreground background;
        selection_foreground = "none";
        selection_background = palette.selection;
        cursor = palette.accent;
        cursor_text_color = palette.background;
        url_color = "#86cdc2";
        active_border_color = palette.accent;
        inactive_border_color = palette.selection;
        tab_bar_background = palette.background;
        active_tab_foreground = palette.background;
        active_tab_background = palette.accent;
        inactive_tab_foreground = "#b9c8c5";
        inactive_tab_background = palette.surface;

        color0 = palette.surface;
        color8 = "#3d5559";
        color1 = "#d9707a";
        color9 = "#e8939a";
        color2 = "#8fbf8a";
        color10 = "#a9d4a3";
        color3 = "#d8b46a";
        color11 = "#e6c98f";
        color4 = "#6a9fc9";
        color12 = "#8db8dc";
        color5 = "#b48ec7";
        color13 = "#c9a9d8";
        color6 = palette.accent;
        color14 = "#86cdc2";
        color7 = "#b9c8c5";
        color15 = "#eef4f2";
      };
      keybindings = {
        "ctrl+shift+enter" = "launch --cwd=current";
        "ctrl+shift+t" = "launch --cwd=current --type=tab";
      };
    };

    plasma.configFile.kdeglobals.General = {
      TerminalApplication = "kitty";
      TerminalService = "kitty.desktop";
    };
  };
}
