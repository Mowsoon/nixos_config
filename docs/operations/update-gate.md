# Update gate

## Overview

A `nix flake update` must not reach `switch` untested. The `update-gate` application of the flake
moves every input to its latest revision in a Git worktree, then evaluates, builds, checks and
diffs the candidate system without activating it. The working tree and its `flake.lock` stay
untouched: the update is accepted by copying the `flake.lock` of the run, and only after the
failures of the run are understood.

The gate starts from the last commit, `HEAD`. Uncommitted changes are left out of the candidate,
and the run records that it left them out. The worktree lives under `~/.cache/update-gate/` and
is removed at the end of the run.

Each run writes its traces under `~/.local/state/update-gate/<date>/`, outside the repository:
the traces are evidence for the triage, not documentation. What the triage concludes goes into an
incident report under `docs/incidents/`, which cites public evidence (a nixpkgs commit, a pull
request, a Hydra build) rather than the local traces.

The run goes through five phases. A failed phase stops only the phases that depend on it:

| Phase | Depends on | What it does |
| --- | --- | --- |
| `update` | | `nix flake update` in the worktree |
| `eval` | `update` | Evaluates the system derivation with `--show-trace` and `keep-going`; the warnings are kept, since a renamed or deprecated option warns before it breaks |
| `build` | `eval` | Builds the candidate with `supply-chain build`, with `keep-going` so that every failing derivation is reached, not only the first |
| `check` | `eval` | `nix flake check --keep-going`: the lints, the service exposure thresholds and the failure drills |
| `diff` | `build` | `supply-chain diff` of the running system against the candidate: packages and vulnerabilities |

The evaluation already builds most of the system. The KWin graft (`system.replaceDependencies`)
reads the references of the system before the graft while it evaluates, an import from
derivation, so Nix builds that system during the `eval` phase. A package that fails to build
therefore usually fails the `eval` phase, and the `build` phase only adds the graft. The failed
derivations are collected from the logs of every phase.

An evaluation error, unlike a build failure, stops the evaluation where it occurs: `keep-going`
reaches every failing derivation, but only the first evaluation error. Fixing it in the worktree
or in a commit reveals the next one, so an update that breaks the evaluation in several places
takes several runs.

The candidate is linked as `result` in the run directory. The link is a garbage collector root:
the candidate stays in the store as long as the run directory exists.

The gate never activates, commits or pushes. The triage of a run follows the procedure below,
by hand or through `update-gate triage`, which hands the run to a Claude Code session without
interaction. The session starts in a worktree of the base commit of the run, so it reads the
configuration that the run evaluated, and it receives this procedure. It may read files, search
the web, and run only `nix eval`, `nix log`, `nix why-depends`, `nix path-info`,
`nix derivation show`, `jq` and `curl` on the GitHub API; it cannot write. Its report, with the
proposed incident reports and configuration change, is written to `triage.md` in the run
directory, and the decision stays manual. The session uses the Claude Code binary of the Claude
desktop app, already allowed by OpenSnitch, and needs one sign-in of that binary.

A replay runs the gate on a past update instead of a new one: `--base` takes the configuration of
another commit than `HEAD`, and `--lock` takes the `flake.lock` of a commit instead of running
`nix flake update`. A replay checks that the gate and its triage still recognise a known failure.
The `diff` phase is skipped, since the running system has nothing to do with a past update.

## How to run the gate

1. From the flake directory, run the gate. It prints each phase and the path of its log as it
   goes; a full run builds the whole system and boots every failure drill.

   ```bash
   nix run .#update-gate
   ```

   The command exits with status 1 when a phase failed.

2. Read the summary printed at the end, or `summary.json` in the run directory. When every phase
   passed, read `diff.txt` and `warnings.txt`, then accept the update.

   ```bash
   cp ~/.local/state/update-gate/<run>/flake.lock flake.lock
   ```

   `<run>` is the date of the run, printed as `Report in ...`.

3. Apply the update as any other change, with `nixos-rebuild test`, then `switch`.

## How to replay a past update

1. Find the commit that moved `flake.lock`, and take its parent as the configuration before the
   update.

   ```bash
   git log --oneline -- flake.lock
   ```

2. Run the gate on that configuration with the lock of that commit.

   ```bash
   nix run .#update-gate -- --base <commit>^ --lock <commit>
   ```

   `<commit>` is the commit found in step 1, and `<commit>^` its parent. The `--` separates the
   options of `nix run` from those of the gate.

3. Triage the run as any other, then compare the result with the incident report of that update.

## How to triage a run with Claude

1. Sign in once with the Claude Code binary of the desktop app. The command opens the browser.

   ```bash
   "$(find ~/.config/Claude/claude-code -name claude -type f | sort -V | tail -n 1)" auth login
   ```

2. Hand the last run, or the run given as argument, to the triage session. It takes a few
   minutes and prints nothing until it ends.

   ```bash
   nix run .#update-gate -- triage [<run>]
   ```

   `<run>` is a run directory under `~/.local/state/update-gate/`; without it, the last run is
   triaged.

3. Read `triage.md` in the run directory, check its evidence, then apply the decisions you accept
   as described in the next sections. `triage.log` holds the errors of the session.

## How to triage a failed run

1. Read the inputs that moved in `inputs.tsv`: name, previous revision and date, new revision and
   date. An input that fails often points to the culprit.

2. Classify each failure from its message, not from the phase where it appeared:

   | Message | Class | Evidence to find |
   | --- | --- | --- |
   | An option renamed, removed, or with a changed type | Configuration | The release notes or the nixpkgs commit |
   | `broken`, `insecure` or a dependency refusal at evaluation | Upstream | The `meta` condition in nixpkgs and the issue it cites |
   | A derivation in `failed-drvs.txt`, from nixpkgs | Upstream | Its Hydra job and the open nixpkgs issues and pull requests |
   | A local patch or override that no longer applies | Configuration | The upstream change that moved the patched code |
   | A failure drill or another flake check | Behaviour change | The drill log, read case by case |
   | `Could not resolve host`, `Timeout was reached`, listed in `network.txt` | Transient | None: run the gate again once the network is back |

   The log of each failed derivation is in `logs/`.

3. For an upstream failure, find the fixing pull request and track it with the nixpkgs PR tracker:
   merged in `master` but not yet in `nixos-unstable` means wait; no fix means report or pin.

4. Choose the narrowest decision: fix the configuration; pin only the broken package from the
   previous nixpkgs revision, as described below; remove the package while it is broken; or keep
   the previous `flake.lock` and wait.

5. Write one incident report per failure in `docs/incidents/<subject>.md`: symptom, cause,
   evidence links, decision, and the exit condition of a workaround, for example "remove the pin
   once pull request N reaches `nixos-unstable`".

## How to pin one package

A pin takes one top-level package, such as `azure-cli`, from an older nixpkgs revision, while the
rest of the update lands. The pin carries the commit and the hash of that revision, so it needs
no flake input and survives `nix flake update`; the evaluation stays pure because the source is
checked against its hash. A package nested in a set, such as `python3Packages.fabric`, cannot be
pinned: pin the package that uses it instead. A pinned package brings the dependencies of its own
revision into the closure.

1. Write the incident report first, in `docs/incidents/<incident>.md`, with the exit condition of
   the pin. The evaluation fails while the report is missing.

2. Read the previous nixpkgs revision of the run that found the failure.

   ```bash
   jq .previousNixpkgs ~/.local/state/update-gate/<run>/summary.json
   ```

   `<run>` is the date of the run.

3. Declare the pin in the `custom` block of `hosts/hephaestus/default.nix`.

   ```nix
   {
     custom.packagePins.azure-cli = {
       rev = "<rev>";
       narHash = "<narHash>";
       incident = "<incident>";
     };
   }
   ```

   `<rev>` and `<narHash>` are the values printed by step 2, and `<incident>` the base name of the
   report of step 1.

4. Run the gate again. `pins.json` of each later run lists the pins still active: once the exit
   condition of a pin is met, remove it and run the gate again.

## Reference

| File in the run directory | Content |
| --- | --- |
| `summary.json` | Base commit, whether the run is a replay and the commit of its lock, the previous nixpkgs revision and its hash, whether uncommitted changes were left out, status and duration of each phase |
| `procedure.md`, `triage.md`, `triage.log` | The procedure given to the triage session, its report, and its errors |
| `pins.json` | The packages pinned by the candidate configuration, or `null` when it does not evaluate |
| `inputs.tsv` | Each input that moved, with its previous and new revision and date |
| `flake.lock`, `flake.lock.old` | The lock of the candidate and the lock of the base commit |
| `<phase>.log` | The full output of a phase |
| `warnings.txt` | The evaluation warnings, each once |
| `errors.txt` | The distinct error messages, such as an evaluation error that fails a check without any failed derivation |
| `network.txt` | The downloads that failed or timed out; a failed derivation that only fetches is then likely transient |
| `failed-drvs.txt` | The derivations whose builder failed, without those that failed only through a dependency |
| `logs/<derivation>.log` | The build log of each failed derivation |
| `result` | The candidate system, when it built |

| Topic | Link |
| --- | --- |
| Hydra | <https://hydra.nixos.org/> |
| nixpkgs PR tracker | <https://nixpk.gs/pr-tracker.html> |
| NixOS release notes | <https://nixos.org/manual/nixos/unstable/release-notes> |
| `nix flake update` | <https://nix.dev/manual/nix/latest/command-ref/new-cli/nix3-flake-update> |
| `git worktree` | <https://git-scm.com/docs/git-worktree> |
