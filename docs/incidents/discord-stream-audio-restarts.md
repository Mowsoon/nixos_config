# Discord restarts the stream audio on every new playback stream

## Overview

In November 2026, viewers of a Discord screen share from the workstation heard the shared audio
slow down and then speed up to catch up, about every few minutes, sometimes with the picture
frozen for up to 1.5 seconds. The voice of the streamer stayed clean. The same share from Windows
on the same machine, with the same quality, did not show it, and the stutter came back on Linux
with a different network uplink. Switching to another video in the shared browser tab triggered
it reliably.

Affected configuration:

| Component | Version |
| --- | --- |
| Discord | 1.0.168, nixpkgs build in an FHS sandbox |
| PipeWire | 1.6.9, with the PulseAudio server `pipewire-pulse` |
| Session | Plasma on Wayland, screen share with system audio |

Cause: on Linux, Discord shares audio by monitoring every PulseAudio sink input, one per
playback stream. `PulseAudioController::MonitorSinkInput` opens a record stream on each new sink
input and reports a success, and `LocalUser::SignalOnSoundshare(true)` then destroys and recreates
the WebRTC audio send stream of the share, through `AudioEngine::DestroyAudioSendStream` and
`LocalUser::CreateAudioStream`, even when a share is already running. A browser creates a new sink
input whenever a page starts new media, so every change of media restarts the stream audio. A
packet capture showed it on the wire: at the millisecond Discord logged the new sink input, the RTP
timestamp of the stream audio jumped back by 76.84 seconds while the sequence numbers stayed
continuous, and the jitter buffer and audio and video synchronisation of the viewer had to start
over.

Ruled out on the way, each with a measurement taken during the stutters:

- the network: the Discord server reported no loss, the interface showed no error and no drop,
  and the packets of the stream left the interface without gaps;
- the hardware encoder: the stutter remained, lighter, with the software VP8 encoder;
- bursts of unpaced packets: the stutter remained with `fq` pacing every flow to 15 Mbit/s;
- the two-second capture buffer that a third-party fix blames: the Discord main process sets
  `PULSE_LATENCY_MSEC=30` before it loads any audio code, and the capture node ran at 30 ms.

Resolution, a workaround until Discord fixes the client: `pkgs/discord-soundshare-fix` builds the
`LD_PRELOAD` library of `discord-linux-soundshare-fix`. When `discord_voice.node` loads, the
library finds `LocalUser::SignalOnSoundshare(bool)` by its ELF symbol and redirects it to a
function that drops a success while a share is already active. The upstream library remembered
the `LocalUser` objects that had started a share and forgot them only on
`SignalOnSoundshare(false)`; Discord 1.0.168 also ends a share through
`LocalUser::SignalOnSoundshareEnded()`, so the next legitimate start would have been dropped and
the stream left without audio. The local patch reads the state byte Discord keeps itself instead,
whose offset it takes from the store in `SignalOnSoundshare` and the clear in
`SignalOnSoundshareEnded`, `0x1f30` in 1.0.168. When a Discord update changes either function, the
library leaves the code untouched, prints `patch skipped safely` on standard error, and Discord
behaves as before.

`home/mowsoon/desktop/apps.nix` wraps the `discord` and `Discord` launchers of the nixpkgs package
to add the library to `LD_PRELOAD`, and the desktop entry starts `Discord` through the wrapper.
Programs that Discord starts inherit the variable; in them the library only relays `dlopen`.
The package test loads the library against a module whose two functions have the instruction
bytes of Discord 1.0.168, and checks that a duplicate start is dropped and that a start after an
end goes through.

Some stutters came with no new sink input nearby; their cause is not established.

## How to verify the workaround

1. Quit Discord from its tray icon, then start it from a terminal with the debug output of the
   library.

   ```bash
   DISCORD_SOUNDSHARE_FIX_DEBUG=1 Discord
   ```

   The output must contain a line that starts with `[discord-soundshare-fix] active for` and ends
   with the state flag offset.

2. Share the screen with audio, play media in a browser and switch to another media. Each switch
   must print this line:

   ```text
   [discord-soundshare-fix] suppressed duplicate soundshare restart
   ```

3. Ask a viewer to confirm that the audio no longer slows down at each switch.

## How to disable the workaround

1. Quit Discord from its tray icon, then start it with the library disabled.

   ```bash
   DISCORD_SOUNDSHARE_FIX_DISABLE=1 Discord
   ```

2. Remove the wrapper from `home/mowsoon/desktop/apps.nix` once a Discord release no longer
   recreates the send stream on a new sink input.

## Reference

| Source | Content |
| --- | --- |
| [zxsleebu/discord-linux-soundshare-fix](https://github.com/zxsleebu/discord-linux-soundshare-fix) | Root cause and the `LD_PRELOAD` hook, commit `1d30b18` |
| [ArenaMMORPG/discord-linux-boost](https://github.com/ArenaMMORPG/discord-linux-boost) | Two-second capture buffer theory, not applicable with `PULSE_LATENCY_MSEC=30` |
| [Discord <3 Linux: A Year of Upgrades](https://discord.com/blog/discord-linux-a-year-of-upgrades) | Linux screen share and planned per-application audio |
