# Supply chain

## Overview

Each system closure of hephaestus gets an inventory of what it contains and a report of the
published vulnerabilities that match it, so that an update or a configuration change can be read
before it is activated. The tool is the `supply-chain` application of the flake, not a flake
check: the scan queries vulnerability databases that change over time and need the network,
which the build sandbox does not have. The report informs; it never blocks an update.

The candidate is the system that the flake would activate, built without activating it. The
`build` command builds it into `./result` of the flake directory, an indirect garbage collector
root, and prints its store path. It takes the flake directory as argument, so the same command
builds the candidate of a Git worktree. Building leaves `/run/current-system` and the boot entries
untouched; only `nixos-rebuild test`, `switch` or `boot` activates a closure.

The `sbom` command describes a closure with sbomnix in three formats: CycloneDX and SPDX, the two
SBOM standards, and a CSV for reading with the shell. Only runtime dependencies are listed, the
store paths the system references, not the compilers that built them. Each component carries its
name, version, derivation, the patches applied by nixpkgs, a CPE and a package URL, which are the
keys a vulnerability scanner matches on.

sbomnix is given the store path of the closure, never a flake reference. Both give the same
components with the same versions, patches, CPE and package URLs; a flake reference adds the
licences and descriptions of nixpkgs, at six times the time and 1.9 GB of memory, and needs the
flake that built the closure, which an older generation no longer has. The SBOMs therefore carry
no licence.

The `scan` command runs vulnxscan, which combines three scanners and reports, per vulnerability
and package, which of them found it:

| Scanner | Source | Match |
| --- | --- | --- |
| grype | Its own database, built from NVD and the distribution advisories | CPE and package URL of the SBOM against the CPE ranges of NVD |
| OSV | `api.osv.dev`, queried for every component with a version | Name and version against the Git tags of the OSV records, mostly OSS-Fuzz crashes |
| vulnix | The NVD feeds, cached in `~/.cache/vulnix` | Name and version of each store path against the NVD ranges |

vulnxscan drops a vulnerability when a patch applied by nixpkgs carries its identifier in its file
name. It ignores the errors of vulnix: a vulnix run that fails leaves a report without its column,
which a later comparison would read as fixed vulnerabilities, so `scan` fails when the `vulnix`
column is missing.

A closure is immutable, so its SBOMs are written once, under
`~/.local/state/supply-chain/<closure>/`, where `<closure>` is the base name of its store path,
and kept after the closure is collected. A candidate that is later activated keeps the same
report. The scan is written in the same directory and rewritten at every run, since the databases
change.

The application is also the `supply-chain` flake check: `nix flake check` only evaluates the
apps of a flake, so without the check a dependency broken by an update would show only at the
next scan. The update of 2026-11-01 brought sbomnix 1.9.0, whose cache libraries sqliteschema and
SimpleSQLite require `typepy<2` while nixpkgs ships typepy 2.0.0. The application builds sbomnix
with a Python package set where both accept typepy 2 (`pythonRelaxDeps`); the interpreter keeps
its store path, so the `python3` rule of OpenSnitch still covers it. A scan of the running system
passed with it. The override goes once nixpkgs builds sbomnix again: check it with
`nix build .#nixosConfigurations.hephaestus.pkgs.sbomnix`.

### Comparing two closures

The `diff` command compares the running system with a candidate, by default
`/run/current-system` and `./result`. It scans both closures in the same run, so that both reports
come from the same state of the databases: a vulnerability published between two scans would
otherwise read as introduced by the candidate. It prints three parts:

- the packages added, removed and upgraded, with the size change of each, from
  `nix store diff-closures`;
- the vulnerabilities fixed, found in the running system and not in the candidate, and the
  vulnerabilities introduced, found only in the candidate, compared by identifier and package and
  without the whitelisted ones;
- an alert listing the introduced vulnerabilities with a CVSS score of 9.0 or more, set by
  `custom.supplyChain.alertScore`.

The result is informative: `diff` exits with success whatever it finds, alert included, because
false positives would make a blocking gate a burden. Two events call for it: after a
`nix flake update`, the main case, and after a configuration change, which mostly brings
transitive dependencies into the closure.

### Weekly scan

The module `modules/security/supply-chain.nix` builds the application for the host, with the Nix
of the system, and the flake app and check reuse that package. It also runs the scan without a
diff, once a week. A laptop is not on at a fixed hour, and a scan needs mains power and the
network, so the schedule is a due date rather than an appointment: a systemd user timer starts
`supply-chain-scan` every hour, and at the next session after a missed hour (`Persistent`). The
service exits at once while the last successful scan, recorded by the date of
`~/.local/state/supply-chain/last-scan`, is less than seven days old, and also on battery
(`ConditionACPower`) or without a connection (`nm-online`). The scan therefore runs in the first
hour, once the week is over, with the machine on mains power and online; a skipped hour costs
nothing and is tried again an hour later. A timer on a weekly date alone would fire once at the
next session and lose the week when that session starts on battery or offline. The scan runs at
the lowest CPU and I/O priority, since it keeps several cores busy for a minute or more, and not
for the system users such as the greeter of SDDM. It ends with a desktop notification, as smartd
does: the summary of the report, the number of open vulnerabilities and of those with a CVSS
score of at least the alert score, and the whitelist entries that expired; or, when the scan
failed, an urgent notification that points to the journal, and the date of the last scan is not
moved, so the next hour tries again. The module owns the OpenSnitch rule of grype, which downloads
its database; the queries of OSV and the NVD feeds of vulnix go through the `python3` rule.

### Provenance

The `provenance` command writes the SLSA v1.0 provenance of a closure with the `provenance` tool of
sbomnix: an in-toto statement whose subject is the store path and its SHA-256 digest, and whose
resolved dependencies are every derivation of the build, recursively, each with its digest. The
build is local, so the builder fields that a hosted builder would fill are set by the command: the
builder is the Nix daemon of the host, the external parameters are the NixOS configuration and the
NixOS version, which carries the date and the revision of nixpkgs, and the end time is the
registration time of the store path. The derivation of the closure must be in the store, which is
true for a closure built on the machine and for the candidate.

This reaches SLSA Build L1 at most: the provenance exists and describes the build, but the machine
that built the closure also writes and could edit the provenance, and nothing signs it. Build L2
and L3 need a hosted builder that signs its provenance, which would need the private input and
build the unfree packages. The provenance is still useful locally: it lists the exact inputs of a
generation, and two provenances can be compared.

### Triage and whitelist

Most findings are not vulnerabilities of the installed code. The matching produces three kinds of
false positives, met on the first scan:

- an NVD range that a scanner cannot compare with the version: a bound given as a date or a Git
  commit, or no bound at all, matches every release, such as 2016 mujs vulnerabilities reported
  against mujs 1.3.6;
- a CPE of another product with the same name, or limited to another platform: knplabs/snappy, a
  PHP library, reported against the snappy compression library, an OpenVPN vulnerability of the
  Windows client;
- a fix that nixpkgs applies under a file name without the identifier, such as the FreePG patch
  of GnuPG for CVE-2022-3219.

A false positive is verified before it is whitelisted: the CPE and the range of the NVD record,
given by `grype db search --vuln <identifier>`, the patches of the package, given by the CSV of
the SBOM and its derivation in nixpkgs, and the references of the record, which link the upstream
issue or merge request that a patch carries. A finding that matches the installed version, or
that cannot be decided, stays in the report.

The whitelist is declared in `tools/supply-chain/whitelist.nix`. Each entry names a vulnerability,
a package, the reason of the decision and an expiry date; evaluation fails when one is missing. At
every scan, the entries whose date has passed are printed as to be triaged again and no longer
hide anything, so a decision cannot outlive the version it was made for. The entries are grouped
by package and reason, with an expiry six months after the triage.

### Limits

- The scan sees only published vulnerabilities: a flaw fixed silently upstream, or not yet
  disclosed, is not reported.
- Every scanner matches by name and version. A fix backported by a nixpkgs patch is still
  reported unless the patch name carries the identifier, and a package that nixpkgs names
  differently from its upstream project is missed or matched to another product.
- OSV records of OSS-Fuzz without a fixing commit mark every later release as affected.
- A source compromised upstream, such as a tampered release archive, matches no record: only
  provenance of the build inputs addresses it.
- sbomnix reads each component from the derivation that the store database records for the path,
  and leaves out a path recorded without one. The paths that `nixos-install` copied from the
  installer image carry no deriver, so a closure that still shares them with the installation has
  holes in its SBOM: openssh, busybox and cpio, among 457 paths of the generation of 2026-10-06. A
  path built or substituted later records its deriver. `sbom` lists those paths in
  `no-deriver.txt` and warns, and `diff` notes them: their vulnerabilities read as fixed or
  introduced although the package did not change.
- The databases change within hours: NVD publishes new records several times a day. Only two
  reports of the same `diff` run are comparable.

## How to inventory the running system

1. Write the SBOMs of the running system. The command prints the report directory.

   ```bash
   nix run .#supply-chain -- sbom
   ```

2. List the components with a version, by name.

   ```bash
   cut -d, -f2,3 <report>/sbom.csv | sort -u | less
   ```

   `<report>` is the directory printed by step 1. Components without a version are configuration
   files and scripts generated by NixOS.

## How to inventory a candidate

1. From the flake directory, build the candidate without activating it.

   ```bash
   nix run .#supply-chain -- build
   ```

   To build the candidate of another checkout, such as a Git worktree, pass its directory:
   `nix run .#supply-chain -- build <directory>`.

2. Write its SBOMs.

   ```bash
   nix run .#supply-chain -- sbom ./result
   ```

## How to scan a closure

1. Scan the running system, or a candidate with `./result` as argument. The first run downloads
   the grype database and the NVD feeds, about six minutes; later runs take about half a minute.
   The command prints the path of the report.

   ```bash
   nix run .#supply-chain -- scan
   ```

2. List the findings that are not whitelisted, by severity.

   ```bash
   tr -d '"' < <report> | grep -v ',True,' | sort -t, -k5,5 -rn | less
   ```

   `<report>` is the path printed by step 1. `tr` removes the quotes so that `sort` reads the CVSS
   score of the fifth column as a number. The columns `grype`, `osv` and `vulnix` hold 1 for the
   scanners that found the line.

## How to triage a finding

1. Read the NVD record as grype holds it: the CPE names the product, the constraint its affected
   versions.

   ```bash
   nix run .#nixosConfigurations.hephaestus.pkgs.grype -- db search --vuln <identifier>
   ```

   `<identifier>` is the `vuln_id` of the finding, such as `CVE-2022-3219`.

2. Read the references of the record, which link the upstream issue and the fixing change.

   ```bash
   nix run .#nixosConfigurations.hephaestus.pkgs.grype -- db search --vuln <identifier> -o json | jq -r '.[].vulnerability.refs[]?.url' | sort -u
   ```

3. List the patches that nixpkgs applies to the package, and compare them with the fixing change.

   ```bash
   grep '^"<package>-' <directory>/sbom.csv | cut -d, -f1,4
   ```

   `<package>` is the package name of the finding; `<directory>` is the report directory.

4. When the finding is a false positive, add it to `tools/supply-chain/whitelist.nix` with its
   reason and an expiry date, then scan again: the line shows `True` in the `whitelist` column.

## How to read the weekly scan

1. Check when the last scan succeeded. A missing file means no scan has succeeded yet.

   ```bash
   date -r ~/.local/state/supply-chain/last-scan
   ```

2. Check when the timer checks next.

   ```bash
   systemctl --user list-timers supply-chain-scan.timer
   ```

3. Read the log of the last run, or force a scan now by removing the date of the last one.

   ```bash
   journalctl --user -u supply-chain-scan -n 20
   rm ~/.local/state/supply-chain/last-scan
   systemctl --user start supply-chain-scan.service
   ```

   On battery, the start is skipped: `ConditionACPower` is not met.

4. Print the summary again, or list the findings with the procedure above.

   ```bash
   nix run .#supply-chain -- summary
   ```

## How to write the provenance of a closure

1. Write the provenance of the running system, or of a candidate with `./result` as argument.

   ```bash
   nix run .#supply-chain -- provenance
   ```

2. Read the subject, the builder fields and the number of build dependencies.

   ```bash
   jq '{subject: .subject[0].uri, builder: .predicate.runDetails.builder.id, parameters: .predicate.buildDefinition.externalParameters, dependencies: (.predicate.buildDefinition.resolvedDependencies | length)}' <file>
   ```

   `<file>` is the path printed by step 1.

## How to review an update before activating it

1. Update the inputs and build the candidate without activating it.

   ```bash
   nix flake update
   nix run .#supply-chain -- build
   ```

2. Compare it with the running system.

   ```bash
   nix run .#supply-chain -- diff | less
   ```

3. Triage each introduced vulnerability as in the previous procedure, alert first.
   Then apply the update with `nixos-rebuild test`, or restore `flake.lock` with
   `git restore flake.lock` to leave it out.

After a configuration change, run steps 1 and 2 without `nix flake update`.

## Reference

| Command | Effect |
| --- | --- |
| `supply-chain build [<flake directory>]` | Builds the `hephaestus` toplevel of the flake into `<flake directory>/result`, default `.`, and prints its store path |
| `supply-chain sbom [<system>]` | Writes the SBOMs of a closure, default `/run/current-system`, and prints the report directory |
| `supply-chain scan [<system>]` | Writes the SBOMs if missing, scans the closure and prints the path of the report |
| `supply-chain diff [<old system>] [<new system>]` | Scans both closures, default `/run/current-system` and `./result`, and prints the packages and vulnerabilities that changed, with an alert on the critical ones introduced |
| `supply-chain summary [<system>]` | Prints the open and critical vulnerabilities of the last scan of a closure, and the expired whitelist entries |
| `supply-chain provenance [<system>]` | Writes the SLSA v1.0 provenance of a closure whose derivation is in the store, and prints its path |

| File in the report directory | Content |
| --- | --- |
| `sbom.cdx.json` | CycloneDX SBOM |
| `sbom.spdx.json` | SPDX SBOM |
| `sbom.csv` | Same components, one line each: name, version, patches, store paths, CPE, package URL |
| `no-deriver.txt` | Paths of the closure recorded without a deriver, missing from the SBOMs |
| `whitelist.csv` | Whitelist entries still valid at the last scan, in the format of vulnxscan |
| `vulns.csv` | Findings of the last scan: identifier, package, version, CVSS score, scanners, whitelist decision and reason |
| `provenance.json` | SLSA v1.0 provenance of the closure |

| Path | Content |
| --- | --- |
| `tools/supply-chain/default.nix` | The `supply-chain` application |
| `modules/security/supply-chain.nix` | Package of the host, weekly scan and its notification, OpenSnitch rule of grype |
| `~/.local/state/supply-chain/last-scan` | Its date is the end of the last successful weekly scan |
| `tools/supply-chain/whitelist.nix` | Triaged false positives, each with its reason and expiry |
| `~/.cache/vulnix` | NVD feeds parsed by vulnix |
| `~/.cache/grype` | Database of grype |

| Measure, 2026-11-03, generation of `nixos-unstable` 2026-10-06 | Value |
| --- | --- |
| Runtime components | 2373, of which 1707 with a version and 399 with nixpkgs patches |
| `sbom` on the store path | 4 s, 150 MB of memory |
| `sbom` on the flake reference, for comparison | 24 s, 1.9 GB of memory; 1132 components gain a licence |
| Report size | 10 MB |
| First `scan`, empty caches | 368 s, 1.7 GB of memory |
| Later `scan` | 35 s |
| `provenance`, recursive, generation of 2026-11-01 | 112 s; 23918 build dependencies; 6.9 MB |
| Findings of the first scan | 340 on 102 packages: 207 found by one scanner, 101 by grype and vulnix together, none by OSV with another scanner |
| After triage | 38 whitelisted; 302 left, of which 14 with a CVSS score of 9 or more and 204 published in 2026, after the pinned nixpkgs revision |
| `diff` of a generation of 2026-10-29 against the running system, same nixpkgs | 62 s; 2 vulnerabilities introduced by the packages added since, both name collisions, whitelisted |
| Update of `nixos-unstable` from 2026-10-06 to 2026-11-01, built in a Git worktree | Candidate built in 484 s once three failures were fixed in the worktree: a removed option, a package broken upstream, KWin patches to rebase |
| `diff` of that update | 182 s; 156 vulnerabilities fixed, 15 introduced, no alert; the 15 are on packages already in the running system but missing from its SBOM for lack of a deriver |

| Tool | Link |
| --- | --- |
| sbomnix and vulnxscan | <https://github.com/tiiuae/sbomnix> |
| grype | <https://github.com/anchore/grype> |
| vulnix | <https://github.com/nix-community/vulnix> |
| OSV | <https://osv.dev/> |
| CycloneDX | <https://cyclonedx.org/specification/overview/> |
| SPDX | <https://spdx.dev/> |
