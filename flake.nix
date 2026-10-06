{
  description = "Declarative NixOS configuration replacing the Arch Linux installation";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      runLint =
        name: tool: command:
        pkgs.runCommand "${name}-check" { nativeBuildInputs = [ tool ]; } ''
          ${command}
          touch $out
        '';
    in
    {
      nixosConfigurations.vm-test = nixpkgs.lib.nixosSystem {
        modules = [ ./hosts/vm-test ];
      };

      formatter.${system} = pkgs.nixfmt-tree;

      checks.${system} = {
        nixfmt = runLint "nixfmt" pkgs.nixfmt "find ${self} -name '*.nix' -exec nixfmt --check {} +";
        statix = runLint "statix" pkgs.statix "statix check ${self}";
        deadnix = runLint "deadnix" pkgs.deadnix "deadnix --fail ${self}";
      };

      devShells.${system}.default = pkgs.mkShell {
        packages = [
          pkgs.nixfmt-tree
          pkgs.statix
          pkgs.deadnix
          pkgs.mkpasswd
        ];
      };
    };
}
