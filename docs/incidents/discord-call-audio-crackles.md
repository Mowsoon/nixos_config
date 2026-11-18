# Discord call audio crackles

## Overview

In November 2026 the audio of Discord calls crackled on the workstation, while Spotify, playing
at the same time through the same output, stayed clean. The voices received from the network were
intact: Discord reported almost no lost packet and only 3 to 27 concealed frames out of about
12,700. The playback side was not: in one 10-second window the Discord playout thread was served
974 times instead of 1000, and each missed period left a gap in the sound.

Affected configuration:

| Component | Version |
| --- | --- |
| Discord | 1.0.168 |
| PipeWire | 1.6.9, with the PulseAudio server `pipewire-pulse` |
| Load | Discord at 164 % of a core and a Nix evaluation running |

Cause: the Discord main process sets `PULSE_LATENCY_MSEC=30` before loading its audio code.
libpulse turns it into a 30 ms target buffer with `PA_STREAM_ADJUST_LATENCY`, and `pipewire-pulse`
gives the call playback stream a latency of `360/48000`, 7.5 ms. PipeWire runs the whole graph at
the smallest period an active stream asks for, rounded down to a power of two, so the driver ran at
256 samples, 5.3 ms, instead of the default 1024. Under load the playback stream of Discord missed
that deadline. Spotify asks for `8192/44100`, 186 ms of buffer, and absorbed the same delays.

Resolution: `modules/hardware/audio.nix` adds a `pipewire-pulse` rule that gives the streams of the
clients whose `application.name` starts with `discord` a floor of 1024 samples for both the
quantum and the request size. The stock configuration of PipeWire uses the same rule for
speech-dispatcher, which also asks for too small a latency and underruns. The call gains about
15 ms of latency.

## How to verify the fix

1. During a call, read the latency of the Discord streams and the period of the graph. The Discord
   streams must show at least `1024` in the `QUANT` column, and the output device must no longer run
   at `256`.

   ```bash
   pw-top -b -n 2 | grep -E 'QUANT|WEBRTC|alsa_output|alsa_input'
   ```

2. Read the playout statistics of Discord. Each line must show close to 1000 callbacks.

   ```bash
   grep -a 'PLAY: 10000msec' ~/.config/discord/logs/discord-webrtc_0 | tail -n 6
   ```

## Reference

| Source | Content |
| --- | --- |
| `share/pipewire/pipewire-pulse.conf` of PipeWire 1.6.9 | `pulse.rules`, and the speech-dispatcher rule with `pulse.min.req` and `pulse.min.quantum` |
| [Discord stream audio restarts](discord-stream-audio-restarts.md) | Where `PULSE_LATENCY_MSEC=30` was found in the Discord code |
