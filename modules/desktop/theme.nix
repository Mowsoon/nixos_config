{
  config,
  inputs,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.custom.theme;
in
{
  imports = [ inputs.stylix.nixosModules.stylix ];

  options.custom.theme = {
    enable = lib.mkEnableOption "the bordeaux palette and the fonts applied to Plasma and GTK";
  };

  config = lib.mkIf cfg.enable {
    stylix = {
      enable = true;
      autoEnable = false;
      polarity = "dark";
      base16Scheme = {
        scheme = "Bordeaux";
        author = "hephaestus";
        base00 = "1a0e11";
        base01 = "26151a";
        base02 = "3a1f27";
        base03 = "6b4a52";
        base04 = "a48a90";
        base05 = "e3d3d6";
        base06 = "f0e4e6";
        base07 = "faf3f4";
        base08 = "e06c75";
        base09 = "d9895b";
        base0A = "d8b46a";
        base0B = "9cba7f";
        base0C = "7fb3ad";
        base0D = "c04a63";
        base0E = "b07fc0";
        base0F = "8c4a3a";
      };
      fonts = {
        sansSerif = {
          package = pkgs.noto-fonts;
          name = "Noto Sans";
        };
        serif = {
          package = pkgs.noto-fonts;
          name = "Noto Serif";
        };
        monospace = {
          package = pkgs.nerd-fonts.jetbrains-mono;
          name = "JetBrainsMono Nerd Font";
        };
        emoji = {
          package = pkgs.noto-fonts-color-emoji;
          name = "Noto Color Emoji";
        };
        sizes = {
          applications = 10;
          desktop = 10;
          popups = 10;
          terminal = 11;
        };
      };
      targets.gtk.enable = true;
    };

    fonts.packages = config.stylix.fonts.packages;

    home-manager.sharedModules = [
      {
        fonts.fontconfig = {
          antialiasing = true;
          hinting = "slight";
          subpixelRendering = "vertical-bgr";
        };

        stylix.targets = {
          kde = {
            enable = true;
            decorations = "org.kde.kwin.aurorae.v2";
            decorationTheme = "__aurorae__svg__AquarelleRed";
            applicationStyle = "Maia_Transparent";
          };
          gtk = {
            enable = true;
            flatpakSupport.enable = false;
          };
        };
      }
    ];
  };
}
