{
  lib,
  writeShellApplication,
  writeText,
  coreutils,
  gawk,
  gnugrep,
  gnused,
  jq,
  nix,
  python3,
  sbomnix,
  host,
  alertScore,
}:
let
  python = python3.override {
    self = python;
    packageOverrides =
      _: prev:
      lib.genAttrs [ "sqliteschema" "simplesqlite" ] (
        name: prev.${name}.overridePythonAttrs { pythonRelaxDeps = [ "typepy" ]; }
      );
  };
  complete = entry: entry ? vuln && entry ? reason && entry ? until;
  whitelist = writeText "whitelist.json" (
    builtins.toJSON (
      map (entry: lib.throwIfNot (complete entry) "whitelist entries need vuln, reason and until" entry) (
        import ./whitelist.nix
      )
    )
  );
in
writeShellApplication {
  name = "supply-chain";
  runtimeInputs = [
    coreutils
    gawk
    gnugrep
    gnused
    jq
    nix
    (sbomnix.override { python3 = python; })
  ];
  text = ''
    state="''${XDG_STATE_HOME:-$HOME/.local/state}/supply-chain"

    usage() {
      echo "usage: supply-chain build [<flake directory>]" >&2
      echo "       supply-chain sbom [<system>]" >&2
      echo "       supply-chain scan [<system>]" >&2
      echo "       supply-chain diff [<old system>] [<new system>]" >&2
      echo "       supply-chain summary [<system>]" >&2
      echo "       supply-chain provenance [<system>]" >&2
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
        nix path-info --json-format 1 --json --recursive "$system" \
          | jq -r 'to_entries[] | select(.value.deriver == null) | .key' > "$work/no-deriver.txt"
        rm -rf "$report"
        mv "$work" "$report"
      fi
      if [ -s "$report/no-deriver.txt" ]; then
        echo "$(wc -l < "$report/no-deriver.txt") paths of $system have no recorded deriver and are missing from its SBOM" >&2
      fi
      echo "$report"
    }

    scan() {
      system=$(realpath "''${1:-/run/current-system}")
      report=$(sbom "$system")
      today=$(date -I)
      jq -r --arg today "$today" '.[] | select(.until < $today)
        | "expired whitelist entry, triage again: \(.vuln) \(.package // "") until \(.until)"' \
        ${whitelist} >&2
      jq -r --arg today "$today" '["vuln_id", "package", "comment"],
        (.[] | select(.until >= $today) | [.vuln, .package // "", "\(.reason) (until \(.until))"])
        | @csv' ${whitelist} > "$report/whitelist.csv"
      (cd "$report" && vulnxscan "$system" --out vulns.csv --whitelist whitelist.csv) >&2
      if ! head -n 1 "$report/vulns.csv" | grep -q '"vulnix"'; then
        echo "vulnix produced no result, the report is incomplete: scan again" >&2
        exit 1
      fi
      echo "$report/vulns.csv"
    }

    open_vulns() {
      tr -d '"' < "$1" | tail -n +2 | awk -F, '$11 != "True" { print $1 "," $3 "," $5 }' | sort -u
    }

    compare() {
      local old new old_vulns new_vulns critical
      old=$(realpath "''${1:-/run/current-system}")
      new=$(realpath "''${2:-./result}")
      old_vulns=$(scan "$old")
      new_vulns=$(scan "$new")
      work=$(mktemp -d)
      trap 'rm -rf "$work"' EXIT
      open_vulns "$old_vulns" > "$work/old"
      open_vulns "$new_vulns" > "$work/new"
      comm -23 "$work/old" "$work/new" > "$work/fixed"
      comm -13 "$work/old" "$work/new" > "$work/introduced"
      awk -F, -v threshold=${alertScore} '$3 != "" && $3 >= threshold' "$work/introduced" > "$work/critical"

      echo "From $old"
      echo "To   $new"
      echo
      echo "Packages:"
      if [ -t 1 ]; then
        nix store diff-closures "$old" "$new"
      else
        nix store diff-closures "$old" "$new" | sed 's/\x1b\[[0-9;]*m//g'
      fi
      echo
      echo "Vulnerabilities fixed: $(wc -l < "$work/fixed")"
      sed 's/^/  /' "$work/fixed"
      echo
      echo "Vulnerabilities introduced: $(wc -l < "$work/introduced")"
      sed 's/^/  /' "$work/introduced"
      for side in "$old_vulns" "$new_vulns"; do
        missing="$(dirname "$side")/no-deriver.txt"
        if [ -s "$missing" ]; then
          echo
          echo "Note: $(wc -l < "$missing") paths of $(basename "$(dirname "$side")") are missing from its inventory, listed in $missing; their vulnerabilities read as fixed or introduced."
        fi
      done
      critical=$(wc -l < "$work/critical")
      if [ "$critical" -gt 0 ]; then
        echo
        echo "ALERT: $critical introduced vulnerabilities with a CVSS score of ${alertScore} or more:"
        sed 's/^/  /' "$work/critical"
      fi
    }

    summary() {
      local system report open critical expired
      system=$(realpath "''${1:-/run/current-system}")
      report="$state/$(basename "$system")"
      if [ ! -e "$report/vulns.csv" ]; then
        echo "no scan of $system yet: run supply-chain scan" >&2
        exit 1
      fi
      open=$(open_vulns "$report/vulns.csv" | wc -l)
      critical=$(open_vulns "$report/vulns.csv" \
        | awk -F, -v threshold=${alertScore} '$3 != "" && $3 >= threshold' | wc -l)
      expired=$(jq --arg today "$(date -I)" '[.[] | select(.until < $today)] | length' ${whitelist})
      echo "$open open vulnerabilities, $critical with a CVSS score of ${alertScore} or more"
      if [ "$expired" -gt 0 ]; then
        echo "$expired whitelist entries to triage again"
      fi
    }

    provenance() {
      local system report drv finished
      system=$(realpath "''${1:-/run/current-system}")
      report=$(sbom "$system")
      if [ ! -e "$report/provenance.json" ]; then
        drv=$(nix-store --query --deriver "$system")
        if [ ! -e "$drv" ]; then
          echo "the derivation of $system is not in the store: build it from the flake first" >&2
          exit 1
        fi
        finished=$(nix path-info --json-format 1 --json "$system" | jq -r '.[].registrationTime')
        PROVENANCE_BUILD_TYPE="https://nix.dev/manual/nix/latest/store/derivation/" \
          PROVENANCE_BUILDER_ID="nix-daemon on ${host}" \
          PROVENANCE_TIMESTAMP_FINISHED="$finished" \
          PROVENANCE_EXTERNAL_PARAMS=$(jq -cn --arg configuration "${host}" --arg version "$(cat "$system/nixos-version")" \
            '{nixosConfiguration: $configuration, nixosVersion: $version}') \
          command provenance --recursive "$drv" --out "$report/provenance.json.tmp" >&2
        mv "$report/provenance.json.tmp" "$report/provenance.json"
      fi
      echo "$report/provenance.json"
    }

    case "''${1:-}" in
      build) shift; build "$@" ;;
      sbom) shift; sbom "$@" ;;
      scan) shift; scan "$@" ;;
      diff) shift; compare "$@" ;;
      summary) shift; summary "$@" ;;
      provenance) shift; provenance "$@" ;;
      *) usage ;;
    esac
  '';
}
