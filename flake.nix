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

    nixos-hardware.url = "github:NixOS/nixos-hardware";

    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    nixvim = {
      url = "github:nix-community/nixvim";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    impermanence = {
      url = "github:nix-community/impermanence";
      inputs = {
        nixpkgs.follows = "";
        home-manager.follows = "";
      };
    };

    nixos-private = {
      url = "git+ssh://git@github.com/Mowsoon/nixos_private";
      flake = false;
    };
  };

  outputs =
    inputs@{
      self,
      nixpkgs,
      disko,
      impermanence,
      lanzaboote,
      ...
    }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      hephaestusModules = [
        disko.nixosModules.disko
        impermanence.nixosModules.impermanence
        lanzaboote.nixosModules.lanzaboote
        ./hosts/hephaestus
      ];
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
          specialArgs = { inherit inputs; };
          modules = hephaestusModules;
        };

        hephaestus-rehearsal = nixpkgs.lib.nixosSystem {
          specialArgs = { inherit inputs; };
          modules = hephaestusModules ++ [ ./hosts/hephaestus/rehearsal.nix ];
        };

        installer = nixpkgs.lib.nixosSystem {
          specialArgs = { inherit inputs; };
          modules = [ ./hosts/installer ];
        };
      };

      apps.${system} = {
        hephaestus-vm = {
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

        rehearsal = {
          type = "app";
          meta.description = "Boot the installer ISO against a blank NVMe disk, Secure Boot firmware in setup mode and a TPM";
          program = nixpkgs.lib.getExe (
            pkgs.callPackage ./tools/rehearsal.nix {
              iso = self.nixosConfigurations.installer.config.system.build.isoImage;
            }
          );
        };
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
