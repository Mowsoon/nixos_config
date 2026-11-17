{ config, lib, ... }:
let
  cfg = config.custom.packagePins;
  nixpkgsAt =
    pin: system:
    import
      (builtins.fetchTree {
        type = "github";
        owner = "NixOS";
        repo = "nixpkgs";
        inherit (pin) rev narHash;
      })
      {
        inherit system;
        inherit (config.nixpkgs) config;
      };
in
{
  options.custom.packagePins = lib.mkOption {
    type = lib.types.attrsOf (
      lib.types.submodule {
        options = {
          rev = lib.mkOption {
            type = lib.types.strMatching "[0-9a-f]{40}";
            description = "nixpkgs commit the package is taken from, usually the revision before the update that broke it.";
          };
          narHash = lib.mkOption {
            type = lib.types.strMatching "sha256-.+";
            description = "Hash of the source of that commit, as `flake.lock` records it, which keeps the evaluation pure.";
          };
          incident = lib.mkOption {
            type = lib.types.str;
            description = "Base name of the incident report under `docs/incidents/` that states why the package is pinned and when the pin goes.";
          };
        };
      }
    );
    default = { };
    description = "Top-level packages taken from another nixpkgs revision than the rest of the system, each tied to its incident report.";
  };

  config = lib.mkIf (cfg != { }) {
    assertions = lib.mapAttrsToList (name: pin: {
      assertion = builtins.pathExists ../../docs/incidents/${pin.incident}.md;
      message = "custom.packagePins.${name}: docs/incidents/${pin.incident}.md does not exist";
    }) cfg;

    nixpkgs.overlays = [
      (_: prev: lib.mapAttrs (name: pin: (nixpkgsAt pin prev.stdenv.hostPlatform.system).${name}) cfg)
    ];
  };
}
