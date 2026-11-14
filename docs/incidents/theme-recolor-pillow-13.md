# theme-recolor refused by Pillow 13

## Overview

On 2026-11-14, the update gate stopped the update of `nixos-unstable` from 2026-11-01 to
2026-11-11 at evaluation:

```text
error: Cannot build '/nix/store/<hash>-theme-recolor-0.1.0.drv'.
       Reason: builder failed with exit code 1.
Checking runtime dependencies for theme_recolor-0.1.0-py3-none-any.whl
  - pillow<13.0,>=12.0 not satisfied by version 13.0.0
```

`pkgs/theme-recolor` declared `pillow = "^12.0"`, which Poetry reads as `>=12.0,<13`. nixpkgs
moved Pillow to 13.0.0, and the runtime dependency check of `buildPythonApplication` refuses a
version outside the declared range. The Plasma themes built with the tool failed with it, and
the system with them. The failure shows in the `eval` phase because the KWin graft builds the
system while it evaluates.

| Component | Version |
| --- | --- |
| `nixos-unstable` | 2026-11-11, `d4f25a3` |
| Pillow | 13.0.0 |
| `theme-recolor` | 0.1.0 |

Cause: the version bound of a package of this repository, not a failure upstream. The tool only
opens, converts, resizes, creates and saves images, and reads pixels with `get_flattened_data`;
its tests pass against Pillow 13.

Decision: the bound becomes `>=12.0,<14`. The build, the tests, mypy and ruff pass against both
nixpkgs revisions, with Pillow 12 and 13.

## Reference

| Source | Content |
| --- | --- |
| [Pillow release notes](https://pillow.readthedocs.io/en/stable/releasenotes/index.html) | What each major version removes |
| [Poetry version constraints](https://python-poetry.org/docs/dependency-specification/#caret-requirements) | The caret requirement `^12.0` stops below 13 |
| [Update gate](../operations/update-gate.md) | The run that found the failure and how it is triaged |
