# Wrong clock blocks DNS and time synchronisation

## Overview

On 2026-10-23, after a debugging session that used `pm_trace`, which stores data in the RTC, the
laptop booted with its clock set to 2040. Name resolution failed (`dig google.com` and
`ping google.com`) while plain IP traffic worked (`ping 1.1.1.1`, `dig @1.1.1.1 google.com`), and
the clock never corrected itself. Setting the date by hand, writing it to the RTC and restarting
chrony and systemd-resolved were needed.

Cause: two services depended on each other through the clock.

- systemd-resolved sends every query to Quad9 over TLS (`DNSOverTLS=true`, no fallback). With the
  clock in 2040, the TLS certificates of the servers are outside their validity, so every query
  fails.
- chrony reaches its NTS servers by name, so it could not contact them without DNS and could not
  correct the clock.
- Once the clock was right, systemd-resolved still did not retry: a clock change only flushes its
  cache (`on_clock_change` in `src/resolve/resolved-manager.c`), while the state of its servers is
  only reset after a resume, a network change or `resolvectl reset-server-features`.
- chrony stepped the clock only during its first three updates (`makestep 0.1 3`); a clock that
  goes wrong later is slewed at a fraction of a millisecond per second.

A failing RTC battery would trigger the same deadlock.

Resolution:

| Change | Module | Effect |
| --- | --- | --- |
| Addresses of `time.cloudflare.com`, `ptbtime1.ptb.de` and `ptbtime2.ptb.de` in `/etc/hosts` | `network/time.nix` | chrony reaches these NTS servers without DNS; their certificates are still verified against the server name, and `nocerttimecheck 1` skips their dates until the first synchronisation |
| `makestep 1 -1` instead of the module default | `network/time.nix` | chrony steps the clock whenever the error exceeds one second |
| Timer `resolved-reset-server-features` with `OnClockChange=true` | `network/dns.nix` | Every clock step runs `resolvectl reset-server-features`, so encrypted DNS is retried at once |

`nts.netnod.se` is not pinned: it rotates between many addresses. The pinned addresses belong to
anycast and institutional services that rarely change; a stale entry only removes that server.

## How to verify the fix

1. Confirm the pinned addresses and the chrony settings.

   ```bash
   grep -E 'time.cloudflare|ptbtime' /etc/hosts
   ```

   ```bash
   grep -E 'makestep|rtc' $(systemctl cat chronyd | grep -o '/nix/store/[^ ]*chrony.conf')
   ```

2. Trigger a clock change without moving the clock, then confirm the timer ran and the resolver
   reset its servers.

   ```bash
   sudo date -s "$(date)"
   ```

   ```bash
   journalctl -b -u resolved-reset-server-features -u systemd-resolved --since -2min | grep -E 'Retry|Resetting learnt'
   ```

## How to refresh the pinned addresses

Run this when a pinned server stops answering in `chronyc -N sources`.

1. Look up the current addresses.

   ```bash
   dig +short A time.cloudflare.com AAAA time.cloudflare.com A ptbtime1.ptb.de A ptbtime2.ptb.de
   ```

2. Update `networking.hosts` in `modules/network/time.nix`, then apply the configuration.

## Reference

| Source | Content |
| --- | --- |
| [chrony.conf(5)](https://chrony-project.org/doc/4.9/chrony.conf.html) | `makestep`, `nocerttimecheck`, `rtcsync` |
| [systemd.timer(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html) | `OnClockChange=` |
| [resolvectl(1)](https://www.freedesktop.org/software/systemd/man/latest/resolvectl.html) | `reset-server-features` |
