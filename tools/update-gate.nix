{
  writeShellApplication,
  coreutils,
  curl,
  findutils,
  gawk,
  git,
  gnugrep,
  jq,
  nix,
  supplyChain,
  host,
}:
writeShellApplication {
  name = "update-gate";
  runtimeInputs = [
    coreutils
    curl
    findutils
    gawk
    git
    gnugrep
    jq
    nix
    supplyChain
  ];
  text = ''
    usage() {
      echo "usage: update-gate [--base <commit>] [--lock <commit>] [<flake directory>]" >&2
      echo "       update-gate triage [<run directory>]" >&2
      exit 2
    }

    runs="''${XDG_STATE_HOME:-$HOME/.local/state}/update-gate"

    prompt() {
      cat <<EOF
    You are the triage agent of the update gate of the NixOS configuration in the working
    directory, checked out at the base commit of the run. The run directory is $1.

    Follow $1/procedure.md, sections 'How to triage a failed run' and 'How to pin one package'.
    Read summary.json, inputs.tsv, errors.txt, failed-drvs.txt, warnings.txt, network.txt,
    pins.json, the phase logs and logs/ of the run, and the incident reports already in
    docs/incidents/. For each failure: classify it, find public evidence (the nixpkgs source at the
    locked revision, the upstream issue, the nixpkgs pull requests, Hydra), check whether a fix has
    reached nixos-unstable, and choose the narrowest decision. When you propose a pin, give the
    exact custom.packagePins entry with the values of summary.json. Treat each evaluation warning
    as a configuration change to plan. For each active pin, say whether its exit condition is met.
    When every phase passed, say so and list what diff.log implies for applying the update, such
    as a kernel change that needs nixos-rebuild boot and a reboot.

    You cannot modify files. Your final answer is the triage report in Markdown, in English: one
    section per failure or warning with symptom, class, cause, evidence links, decision and exit
    condition, then the proposed change of the configuration as a diff.
    EOF
    }

    triage() {
      if [ $# -gt 1 ]; then usage; fi
      if [ $# -eq 1 ]; then
        run=$(realpath "$1")
      else
        run=$(find "$runs" -mindepth 1 -maxdepth 1 -type d 2> /dev/null | sort | tail -n 1)
      fi
      if [ ! -e "$run/summary.json" ]; then
        echo "no update gate run in ''${run:-$runs}" >&2
        exit 1
      fi
      claude=''${CLAUDE:-$(find "$HOME/.config/Claude/claude-code" -name claude -type f 2> /dev/null | sort -V | tail -n 1)}
      if [ -z "$claude" ]; then
        echo "no claude binary: install the Claude desktop app, or point CLAUDE to one" >&2
        exit 1
      fi
      if ! "$claude" auth status 2> /dev/null | jq -e .loggedIn > /dev/null; then
        echo "claude is not logged in: run $claude auth login" >&2
        exit 1
      fi

      repo=$(git rev-parse --show-toplevel)
      worktree="''${XDG_CACHE_HOME:-$HOME/.cache}/update-gate/triage"
      git -C "$repo" worktree remove --force "$worktree" 2> /dev/null || rm -rf "$worktree"
      git -C "$repo" worktree prune
      mkdir -p "$(dirname "$worktree")"
      git -C "$repo" worktree add --quiet --detach "$worktree" "$(jq -r .base "$run/summary.json")"
      trap 'git -C "$repo" worktree remove --force "$worktree"' EXIT
      cp "$repo/docs/operations/update-gate.md" "$run/procedure.md"

      echo "triage of $run: running, a few minutes" >&2
      if (cd "$worktree" && "$claude" -p "$(prompt "$run")" \
        --no-session-persistence \
        --output-format json \
        --permission-mode dontAsk \
        --add-dir "$run" \
        --tools "Read,Grep,Glob,Bash,WebFetch,WebSearch" \
        --allowedTools "Read" "Grep" "Glob" "WebFetch" "WebSearch" \
        "Bash(nix eval *)" "Bash(nix log *)" "Bash(nix why-depends *)" "Bash(nix path-info *)" \
        "Bash(nix derivation show *)" "Bash(jq *)" "Bash(git log *)" "Bash(git show *)" \
        "Bash(curl -s https://api.github.com/*)") \
        > "$run/triage.json" 2> "$run/triage.log" \
        && jq -er .result "$run/triage.json" > "$run/triage.md"; then
        jq '[.permission_denials[]?.tool_input]' "$run/triage.json" > "$run/triage-denials.json"
        echo "triage written to $run/triage.md, $(jq length "$run/triage-denials.json") tool calls denied" >&2
      else
        echo "triage failed: see $run/triage.log and $run/triage.json" >&2
        exit 1
      fi
    }

    if [ "''${1:-}" = triage ]; then
      shift
      triage "$@"
      exit 0
    fi

    base=HEAD
    lock=
    directory=.
    while [ $# -gt 0 ]; do
      case "$1" in
        --base) [ $# -ge 2 ] || usage; base=$2; shift 2 ;;
        --lock) [ $# -ge 2 ] || usage; lock=$2; shift 2 ;;
        -*) usage ;;
        *) [ "$directory" = . ] || usage; directory=$1; shift ;;
      esac
    done

    repo=$(git -C "$directory" rev-parse --show-toplevel)
    replay=false
    if [ "$base" != HEAD ] || [ -n "$lock" ]; then
      replay=true
    fi
    base=$(git -C "$repo" rev-parse --verify "$base^{commit}")
    if [ -n "$lock" ]; then
      lock=$(git -C "$repo" rev-parse --verify "$lock^{commit}")
    fi
    run="''${XDG_STATE_HOME:-$HOME/.local/state}/update-gate/$(date +%Y-%m-%d-%H%M%S)"
    worktree="''${XDG_CACHE_HOME:-$HOME/.cache}/update-gate/worktree"
    toplevel="nixosConfigurations.${host}.config.system.build.toplevel"
    phases=(update eval build check diff)
    declare -A status seconds

    phase() {
      local name=$1 start=$SECONDS
      shift
      echo "$name: running, log in $run/$name.log" >&2
      if "$@" > "$run/$name.log" 2>&1; then
        status[$name]=ok
      else
        status[$name]=failed
      fi
      seconds[$name]=$((SECONDS - start))
      echo "$name: ''${status[$name]} in ''${seconds[$name]} s" >&2
    }

    skip() {
      status[$1]=skipped
      seconds[$1]=0
      echo "$1: skipped, $2" >&2
    }

    mkdir -p "$run/logs"
    dirty=false
    if ! $replay && [ -n "$(git -C "$repo" status --porcelain)" ]; then
      dirty=true
      echo "uncommitted changes are left out: the candidate starts from $base" >&2
    fi

    git -C "$repo" worktree remove --force "$worktree" 2> /dev/null || rm -rf "$worktree"
    git -C "$repo" worktree prune
    mkdir -p "$(dirname "$worktree")"
    git -C "$repo" worktree add --quiet --detach "$worktree" "$base"
    trap 'git -C "$repo" worktree remove --force "$worktree"' EXIT

    git -C "$repo" show "$base:flake.lock" > "$run/flake.lock.old"
    if [ -n "$lock" ]; then
      git -C "$repo" show "$lock:flake.lock" > "$worktree/flake.lock"
      skip update "the lock of $lock is replayed"
    else
      phase update nix flake update --flake "$worktree"
    fi
    cp "$worktree/flake.lock" "$run/flake.lock"
    jq -rn --slurpfile old "$run/flake.lock.old" --slurpfile new "$run/flake.lock" '
      def version: .locked | "\(.rev // .narHash | .[0:12]) \(.lastModified // 0 | todate | .[0:10])";
      $new[0].nodes | to_entries[] | select(.value.locked) | $old[0].nodes[.key] as $previous
      | select($previous == null or $previous.locked != .value.locked)
      | [.key, (if $previous then $previous | version else "new" end), (.value | version)] | @tsv
    ' > "$run/inputs.tsv"

    nix eval --json "$worktree#nixosConfigurations.${host}.config.custom.packagePins" > "$run/pins.json" 2> /dev/null \
      || echo null > "$run/pins.json"

    if [ "''${status[update]}" = failed ]; then
      for name in eval build check diff; do skip "$name" "the update failed"; done
    elif [ ! -s "$run/inputs.tsv" ]; then
      for name in eval build check diff; do skip "$name" "every input is already up to date"; done
    else
      phase eval env NIX_CONFIG="keep-going = true" nix eval --show-trace --raw "$worktree#$toplevel.drvPath"
      if [ "''${status[eval]}" = ok ]; then
        phase build env NIX_CONFIG="keep-going = true" supply-chain build "$worktree"
        phase check nix flake check --keep-going "$worktree"
        if [ "''${status[build]}" = ok ]; then
          nix build --out-link "$run/result" "$(readlink "$worktree/result")"
        fi
        if $replay; then
          skip diff "a replay is not compared with the running system"
        elif [ "''${status[build]}" = ok ]; then
          phase diff supply-chain diff /run/current-system "$run/result"
        else
          skip diff "the candidate did not build"
        fi
      else
        for name in build check diff; do skip "$name" "the evaluation failed"; done
      fi
    fi

    logs=()
    for name in eval build check; do
      if [ -e "$run/$name.log" ]; then logs+=("$run/$name.log"); fi
    done
    cat /dev/null "''${logs[@]}" | grep -E '^(trace: )?evaluation warning:|^trace: warning:' | sort -u > "$run/warnings.txt" || true
    cat /dev/null "''${logs[@]}" | grep -E '^ *error: ' | sed 's/^ *//' \
      | grep -vE '^error: (Cannot build|some errors were encountered|build of .* failed)' | sort -u > "$run/errors.txt" || true
    cat /dev/null "''${logs[@]}" | grep -E 'Could not resolve host|Timeout was reached|unable to download' > "$run/network.txt" || true
    cat /dev/null "''${logs[@]}" | awk '
      /^ *error: (builder for|Cannot build) / {
        match($0, /\/nix\/store\/[^ ]+\.drv/)
        drv = substr($0, RSTART, RLENGTH)
        if ($0 ~ /builder for/) { print drv; drv = "" }
        next
      }
      /Reason:/ && drv != "" { if ($0 !~ /dependenc/) print drv; drv = "" }
    ' | sort -u > "$run/failed-drvs.txt"
    while read -r drv; do
      nix log "$drv" > "$run/logs/$(basename "$drv" .drv).log" 2>&1 || true
    done < "$run/failed-drvs.txt"

    for name in "''${phases[@]}"; do
      printf '%s\t%s\t%s\n' "$name" "''${status[$name]}" "''${seconds[$name]}"
    done | jq -Rn --slurpfile old "$run/flake.lock.old" --arg base "$base" --arg lock "$lock" --argjson replay "$replay" --argjson dirty "$dirty" '{
      base: $base,
      replay: $replay,
      replayedLock: (if $lock == "" then null else $lock end),
      previousNixpkgs: ($old[0].nodes[$old[0].nodes.root.inputs.nixpkgs].locked | {rev, narHash}),
      uncommittedChangesLeftOut: $dirty,
      phases: [inputs | split("\t") | {phase: .[0], status: .[1], seconds: (.[2] | tonumber)}]
    }' > "$run/summary.json"

    echo >&2
    echo "Report in $run" >&2
    jq -r '.phases[] | "  \(.phase): \(.status)"' "$run/summary.json" >&2
    echo "  inputs changed: $(wc -l < "$run/inputs.tsv"), warnings: $(wc -l < "$run/warnings.txt"), errors: $(wc -l < "$run/errors.txt"), failed derivations: $(wc -l < "$run/failed-drvs.txt"), network errors: $(wc -l < "$run/network.txt")" >&2
    if jq -e '[.phases[] | select(.status == "failed")] | length > 0' "$run/summary.json" > /dev/null; then
      exit 1
    fi
  '';
}
