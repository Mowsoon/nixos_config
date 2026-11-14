{ pkgs, ... }:
let
  soundshareFix = pkgs.callPackage ../../../pkgs/discord-soundshare-fix/package.nix { };
  discordWithSoundshareFix = pkgs.symlinkJoin {
    inherit (pkgs.discord) name;
    paths = [ pkgs.discord ];
    nativeBuildInputs = [ pkgs.makeWrapper ];
    postBuild = ''
      for program in discord Discord; do
        wrapProgram "$out/bin/$program" \
          --prefix LD_PRELOAD : ${soundshareFix}/lib/libdiscord_soundshare_fix_preload.so
      done
    '';
  };
in
{
  home.packages = with pkgs; [
    discordWithSoundshareFix
    spotify
    libreoffice-qt
    solaar
  ];

  programs.obsidian.enable = true;

  services.opensnitch-ui.enable = true;
}
