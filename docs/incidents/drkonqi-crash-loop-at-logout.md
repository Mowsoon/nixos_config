# DrKonqi crashes in a loop at logout

## Overview

Every logout and login on 2026-10-27 left a crash notification for
`drkonqi-coredump-launcher`, and `coredumpctl` listed a new core dump of it about twice per
second for as long as the session was ending: more than twenty within seven seconds at 23:01.

Each launcher stopped on a fatal Qt error before creating its first window:

```text
drkonqi-coredump-launcher: could not connect to display
drkonqi-coredump-launcher: This application failed to start because no Qt platform plugin could be initialized.
```

Affected configuration:

| Component | Version |
| --- | --- |
| Plasma | 6.7.5, DrKonqi 6.7.5 |
| systemd | `systemd-coredump` with `drkonqi-coredump-processor@` wanted by every `systemd-coredump@` |

Cause: at logout, components such as `xdg-desktop-portal-kde` and `ksecretd` crash when the
Wayland compositor goes away. The Plasma module of NixOS makes `drkonqi-coredump-processor@` run
for every core dump, and the processor starts `drkonqi-coredump-launcher` in the user session to
show the crash dialog. With the compositor gone, the launcher cannot reach a display, aborts, and
dumps core itself, which starts a new processor and a new launcher. The loop runs until the user
manager stops, and its last crash is reported at the next login.

Resolution: `modules/desktop/plasma.nix` masks `drkonqi-coredump-processor@`. Core dumps are still
recorded by `systemd-coredump` and listed by `coredumpctl`; KDE no longer opens its crash dialog.

## How to verify the fix

1. Confirm the processor unit is masked. The command must print `masked`.

   ```bash
   systemctl is-enabled drkonqi-coredump-processor@.service
   ```

2. Log out and log in again, then list the core dumps of the launcher since the logout. The
   command must print nothing.

   ```bash
   coredumpctl list --since -10min --no-pager | grep drkonqi
   ```

## Reference

| Source | Content |
| --- | --- |
| [DrKonqi](https://invent.kde.org/plasma/drkonqi) | Processor and launcher of the coredumpd integration |
| `man systemd-coredump` | Recording and listing of core dumps |
