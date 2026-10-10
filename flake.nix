{
  description = "Declarative NixOS configuration replacing the Arch Linux installation";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    disko = {
      url = "github:nix-community/disko";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    lanzaboote = {
      url = "github:nix-community/lanzaboote/v1.2.0";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    impermanence = {
      url = "github:nix-community/impermanence";
      inputs = {
        nixpkgs.follows = "";
        home-manager.follows = "";
      };
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      disko,
      impermanence,
      lanzaboote,
    }:
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
      nixosConfigurations = {
        vm-test = nixpkgs.lib.nixosSystem {
          modules = [ ./hosts/vm-test ];
        };

        hephaestus = nixpkgs.lib.nixosSystem {
          modules = [
            disko.nixosModules.disko
            impermanence.nixosModules.impermanence
            lanzaboote.nixosModules.lanzaboote
            ./hosts/hephaestus
          ];
        };
      };

      apps.${system}.hephaestus-vm = {
        type = "app";
        meta.description = "Boot the hephaestus disko VM from a blank firmware and TPM";
        program = nixpkgs.lib.getExe (
          pkgs.writeShellApplication {
            name = "hephaestus-vm";
            text = ''
              rm -rf hephaestus-efi-vars.fd hephaestus-swtpm
              exec ${self.nixosConfigurations.hephaestus.config.system.build.vmWithDisko}/bin/disko-vm "$@"
            '';
          }
        );
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
