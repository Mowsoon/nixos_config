{
  config,
  inputs,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.custom.theme;
  scheme = {
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
  recolor = pkgs.callPackage ../../pkgs/theme-recolor/package.nix { };
  palette = pkgs.writeText "bordeaux-palette.json" (
    builtins.toJSON (
      removeAttrs scheme [
        "scheme"
        "author"
      ]
    )
  );
  families = [
    "red"
    "orange"
    "yellow"
    "green"
    "cyan"
    "blue"
    "purple"
    "pink"
    "brown"
  ];
  accentOnly = lib.genAttrs families (_: "base0D");
  recolored =
    {
      name,
      source,
      target,
      roles ? { },
      postRecolor ? "",
    }:
    pkgs.runCommand "${lib.toLower name}-bordeaux" { nativeBuildInputs = [ recolor ]; } ''
      mkdir -p $out/share/${target}
      cp -r ${inputs.nixos-private}/themes/${source} $out/share/${target}/${name}
      chmod -R u+w $out
      theme-recolor --palette ${palette} ${
        lib.concatStringsSep " " (lib.mapAttrsToList (family: slot: "--role ${family}=${slot}") roles)
      } $out/share/${target}/${name}
      ${postRecolor}
    '';
  plasmaStyle = recolored {
    name = "Maia_Transparent";
    source = "desktoptheme/Maia_Transparent";
    target = "plasma/desktoptheme";
    roles.cyan = "base0D";
    postRecolor = "rm $out/share/plasma/desktoptheme/Maia_Transparent/colors";
  };
  decoration = recolored {
    name = "AquarelleRed";
    source = "aurorae/AquarelleRed";
    target = "aurorae/themes";
  };
  icons = recolored {
    name = "Material-Black-Mango-Numix";
    source = "icons/Material-Black-Mango-Numix";
    target = "icons";
    postRecolor = ''
      substituteInPlace $out/share/icons/Material-Black-Mango-Numix/index.theme \
        --replace-fail "Inherits=gnome,hicolor" "Inherits=breeze-dark,hicolor"
    '';
  };
  cursor = recolored {
    name = "Rage-Gothic-Light";
    source = "cursors/Rage-Gothic-Light";
    target = "icons";
    roles = accentOnly;
  };
  splash = recolored {
    name = "Jolly-Splash-6";
    source = "look-and-feel/Jolly-Splash-6";
    target = "plasma/look-and-feel";
    roles = accentOnly;
  };
  wallpaper = pkgs.runCommand "wallpaper.png" { } ''
    cp ${inputs.nixos-private}/wallpapers/desktop.png $out
  '';
  avatar = pkgs.runCommand "avatar.png" { } ''
    cp ${inputs.nixos-private}/avatars/mowsoon.png $out
  '';
  waitForPlasmaShell = ''
    attempt=0
    until qdbus org.kde.plasmashell /PlasmaShell 2>/dev/null | grep -q evaluateScript; do
      attempt=$((attempt + 1))
      [ "$attempt" -ge 240 ] && break
      sleep 0.5
    done
  '';
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
      base16Scheme = scheme;
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
      cursor = {
        package = cursor;
        name = "Rage-Gothic-Light";
        size = 24;
      };
      targets.gtk.enable = true;
    };

    fonts.packages = config.stylix.fonts.packages;

    home-manager.sharedModules = [
      (
        { config, lib, ... }:
        let
          inherit (config.programs.plasma) workspace;
        in
        {
          home = {
            file.".face.icon".source = avatar;
            packages = [
              plasmaStyle
              decoration
              icons
              splash
            ];
            activation.stylixLookAndFeel = lib.mkForce (lib.hm.dag.entryAnywhere "");
          };

          fonts.fontconfig = {
            antialiasing = true;
            hinting = "slight";
            subpixelRendering = "vertical-bgr";
          };

          programs.plasma = {
            enable = true;
            workspace = {
              colorScheme = scheme.scheme;
              theme = "Maia_Transparent";
              iconTheme = "Material-Black-Mango-Numix";
              splashScreen.theme = "Jolly-Splash-6";
              windowDecorations = {
                library = "org.kde.kwin.aurorae.v2";
                theme = "__aurorae__svg__AquarelleRed";
              };
              inherit wallpaper;
            };
            startup.startupScript.wait_for_plasmashell = {
              priority = 0;
              runAlways = true;
              text = waitForPlasmaShell;
            };
            kscreenlocker.appearance = {
              inherit wallpaper;
            };
            panels = [
              {
                location = "left";
                floating = true;
                height = 46;
                widgets = [
                  "org.kde.plasma.kickoff"
                  "org.kde.plasma.pager"
                  "org.kde.plasma.icontasks"
                  "org.kde.plasma.marginsseparator"
                  "org.kde.plasma.systemtray"
                  "org.kde.plasma.digitalclock"
                  "org.kde.plasma.showdesktop"
                ];
              }
            ];
          };

          xdg.autostart.entries = lib.mkForce [ ];

          gtk.iconTheme = {
            name = workspace.iconTheme;
            package = icons;
          };

          stylix.targets = {
            kde.enable = true;
            gtk = {
              enable = true;
              flatpakSupport.enable = false;
            };
          };
        }
      )
    ];
  };
}
