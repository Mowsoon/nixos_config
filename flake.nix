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

    plasma-manager = {
      url = "github:nix-community/plasma-manager";
      inputs = {
        nixpkgs.follows = "nixpkgs";
        home-manager.follows = "home-manager";
      };
    };

    stylix = {
      url = "github:nix-community/stylix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    nix-index-database = {
      url = "github:nix-community/nix-index-database";
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

    dublinlife = {
      url = "git+ssh://git@github.com/Mowsoon/DublinLife";
      inputs.nixpkgs.follows = "nixpkgs";
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
      rgbEffects = pkgs.callPackage ./pkgs/rgb-effects/package.nix { };
      themeRecolor = pkgs.callPackage ./pkgs/theme-recolor/package.nix { };
      drills = import ./tests/drills { inherit pkgs inputs; };
      hephaestusModules = [
        disko.nixosModules.disko
        impermanence.nixosModules.impermanence
        lanzaboote.nixosModules.lanzaboote
        ./hosts/hephaestus
      ];
      hephaestus = self.nixosConfigurations.hephaestus.config;
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

        kernel-test = nixpkgs.lib.nixosSystem {
          modules = [ ./hosts/kernel-test ];
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

        kernel-vm = {
          type = "app";
          meta.description = "Boot a kernel build directory in the kernel-test VM, with the kernel sources shared on /src";
          program = nixpkgs.lib.getExe (
            pkgs.callPackage ./tools/kernel-vm.nix {
              vm = self.nixosConfigurations.kernel-test.config.system.build.vm;
            }
          );
        };

        supply-chain = {
          type = "app";
          meta.description = "Build the hephaestus candidate without activating it, inventory a system closure and scan it for known vulnerabilities";
          program = nixpkgs.lib.getExe (
            self.nixosConfigurations.hephaestus.pkgs.callPackage ./tools/supply-chain {
              nix = hephaestus.nix.package;
              host = "hephaestus";
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

      packages.${system} = {
        rgb-effects = rgbEffects;
        theme-recolor = themeRecolor;
        kernel-vm-modules = pkgs.callPackage ./tools/kernel-vm-modules.nix { };
        vmlinux-h = pkgs.callPackage ./tools/vmlinux-h.nix {
          inherit (self.nixosConfigurations.hephaestus.config.boot.kernelPackages) kernel;
        };
      };

      formatter.${system} = pkgs.nixfmt-tree;

      checks.${system} = {
        nixfmt = runLint "nixfmt" pkgs.nixfmt "find ${self} -name '*.nix' -exec nixfmt --check {} +";
        statix = runLint "statix" pkgs.statix "statix check ${self}";
        deadnix = runLint "deadnix" pkgs.deadnix "deadnix --fail ${self}";
        rgb-effects = rgbEffects;
        rgb-effects-ruff = rgbEffects.lints.ruff;
        rgb-effects-mypy = rgbEffects.lints.mypy;
        theme-recolor = themeRecolor;
        theme-recolor-ruff = themeRecolor.lints.ruff;
        theme-recolor-mypy = themeRecolor.lints.mypy;
        service-exposure = pkgs.callPackage ./tools/service-exposure.nix {
          systemd = hephaestus.systemd.package;
          units = hephaestus.environment.etc."systemd/system".source;
          thresholds = hephaestus.custom.hardening.serviceExposure;
        };
      }
      // nixpkgs.lib.mapAttrs' (name: nixpkgs.lib.nameValuePair "drill-${name}") drills;

      devShells.${system} = {
        kernel = pkgs.callPackage ./tools/kernel-shell.nix { };

        default = pkgs.mkShell {
          packages = [
            pkgs.nixfmt-tree
            pkgs.statix
            pkgs.deadnix
            pkgs.mkpasswd
          ];
        };
      };
    };
}
