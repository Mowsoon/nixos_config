{
  writeShellApplication,
  coreutils,
  nix,
  sbomnix,
  host,
}:
writeShellApplication {
  name = "supply-chain";
  runtimeInputs = [
    coreutils
    nix
    sbomnix
  ];
  text = ''
    state="''${XDG_STATE_HOME:-$HOME/.local/state}/supply-chain"

    usage() {
      echo "usage: supply-chain build [<flake directory>]" >&2
      echo "       supply-chain sbom [<system>]" >&2
      exit 2
    }

    build() {
      flake=$(realpath "''${1:-.}")
      nix build "$flake#nixosConfigurations.${host}.config.system.build.toplevel" \
        --out-link "$flake/result" --print-out-paths
    }

    sbom() {
      system=$(realpath "''${1:-/run/current-system}")
      report="$state/$(basename "$system")"
      if [ ! -e "$report/sbom.cdx.json" ]; then
        mkdir -p "$state"
        work=$(mktemp -d "$state/.work.XXXXXX")
        (cd "$work" && sbomnix "$system" --csv sbom.csv --cdx sbom.cdx.json --spdx sbom.spdx.json) >&2
        rm -rf "$report"
        mv "$work" "$report"
      fi
      echo "$report"
    }

    case "''${1:-}" in
      build) shift; build "$@" ;;
      sbom) shift; sbom "$@" ;;
      *) usage ;;
    esac
  '';
}
