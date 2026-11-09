# TorchRoll

**A playable late-night torch-ballad keyboard for your MIDI keys. Hold a chord and a slow triplet roll engine comps it (rolled chords, triplet arps, grace-note leans, tempo-locked tremolo) over a breath pad, an upright-style bass and brushes, on the grid of your BPM, key and chords. Record a take and export a DAW-ready WAV and MIDI that land on bar 1.** Live: **https://torchroll.vercel.app**

Theme: sultry ballad. Why it exists: people want a 6/8 ballad arpeggio played back to them at their own tempo ([@strawberrieVT, Sep 2026](https://x.com/strawberrieVT/status/2103211525398028760): "sing or play this lick to me in 6/8 at 60bpm and 120bpm… this arpeggio"), and EP/ballad keys normally live inside a DAW sampler ([FL Keys post](https://x.com/Dane2088255Dane/status/2083649314648395991)). TorchRoll makes the ballad comping itself the instrument: play it live from a MIDI keyboard in the browser at your BPM, nothing to install.

## Play it
1. **Your loop:** BPM (60–180), key, mode, bars (4/8/16) and chords (one per bar, e.g. `Am9 Dm9 Gsus4 Cmaj7`). Saved in your browser; changing the key transposes your chords and take.
2. **Play:** your MIDI keyboard plays the EP right away and never starts the transport. Press **▶ Play roll + band** to run the roll engine, breath pad, bass and brushes on the audio clock.
3. **Roll engine:** 7 recipes (Torch Roll, Midnight Triplets, Slow Burn, Lean Back, Smoke Rings, Lounge Quarters, Hold). 12 triplet steps per 4/4 bar (R roll / A arp / B block / L low note / G grace lean / H hold / - rest). Ring, roll spread, tremolo, breath, drums. Every change lands on the next step, no restart.
4. **Voice:** Velvet Tine (synth FM EP), Satin Bell (synth FM bell-piano), Smoke Reed (synth reedy EP). Brightness, attack (real ramp), release (≥10 ms). Scale lock.
5. **Rec take:** each pass overdubs your voicings onto the loop; the take feeds the roll engine and the export.

## MIDI controls
Notes + velocity · **CC64** sustain · **CC1** mod wheel = tremolo depth · **CC74** = brightness · **CC11** expression / **CC2** breath = pad breath · pitch bend ±2 · CC123 all notes off. MIDI in/out select; MIDI out mirrors keys (ch 1), bass (ch 3), brushes (ch 10). Audio output select (setSinkId, falls back to system default). No audio input.

## Export
`torchroll-<recipe>-<bpm>bpm-<key>.wav`: 48 kHz / 24-bit stereo, exactly `bars × 4 × 60 / bpm × 48000` samples, downbeat at sample 0, ring-out + room tail folded back, peak −1.1 dBFS. Matching `.mid`: tempo, 4/4, key signature, chord markers, one track per chair (Torch Keys, Breath Pad, Velvet Bass, Brush Kit). Deterministic (seeded noise, no Math.random).

## Sounds
Every voice is synthesized in the browser and named as a synth. No samples, no third-party requests.

## Price
$19 one-time via Lemon Squeezy license key (gate checks store_id + product_id). The config is empty right now, so the button says "Checkout opening soon" and full exports are free.

## QA
`python3 qa/s9.py <url> checks/s9-live.json` runs all 7 AUDIO-ENGINE-RULES section 9 checks plus MIDI keyboard, MIDI file, stop-silence and persistence checks. `qa/no_unpinned.sh` is check 7.
