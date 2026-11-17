{
  writeShellApplication,
  coreutils,
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
      exit 2
    }

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
    done | jq -Rn --arg base "$base" --arg lock "$lock" --argjson replay "$replay" --argjson dirty "$dirty" '{
      base: $base,
      replay: $replay,
      replayedLock: (if $lock == "" then null else $lock end),
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
