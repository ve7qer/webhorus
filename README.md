# webhorus — performance fork

This fork of [projecthorus/webhorus](https://github.com/projecthorus/webhorus) reduces CPU usage. The demodulators
themselves (C compiled to WebAssembly) were already fine. Most of the time was going into Python
loops, data copying and conversions around them.

## What was optimized

**Biggest win — Horus audio input.** Every 2.7 ms the AudioWorklet rebuilt its entire sample buffer
(`Array.concat` / `splice`), which kept about 78% of a CPU core busy on the audio thread. It now uses a
preallocated typed-array buffer, and the cost is effectively zero.

**Wenet (high-speed images)**
- The packet framer (unique-word search, de-framing, LDPC decode and CRC check) ran a Python loop for
  every received bit, about 100,000 iterations a second. It is now in C (`pywenet/drs232_framer.c`).
- Python was called about 2,000 times a second with tiny 480-sample blocks. A batch demodulator now
  handles a whole buffer in one call. Packets that complete in the same batch are no longer dropped.
- IQ samples went JS Array → Python list → `struct.pack` → `bytes` slicing. They now go to the worker as
  a transferred `Float32Array` and reach the modem with no copy.

**Horus (balloon telemetry)**
- Modem stats were converted to Python dicts two or three times per chunk, including the large eye-diagram
  and symbol arrays that nothing uses. Now only the few fields the UI needs are read, once per chunk.
- Audio is passed to the demodulator as raw bytes instead of being converted value by value.

**UI**
- The Plotly heatmap waterfall re-processed the whole buffer and sorted every value on each update.
  It is replaced by a small canvas renderer that takes about 0.4 ms per update.
- SSDV images were converted to a base64 string one byte at a time on each update. They now use Blob URLs.

## Results

Measured old vs new with the real WebAssembly builds (Pyodide 0.29):

| Mode / part | Before | After |
|---|---|---|
| Horus audio input | 78% of a core | ~0% |
| Wenet worker | 34% of a core | 5% |
| Wenet main thread | 17% of a core | 1.4% |
| Horus main thread | 2.5% of a core | 0.3% |

Decoding output is unchanged. On recorded and simulated test signals the new code decodes exactly the
same packets as the original: 60/60 Wenet test packets, and identical frames and stats on
horusdemodlib's sample recordings. It has not yet been tested with a live radio.

## Building

It's advised not to install this python package locally as it will break horusdemodlib packages.

Build the wheels (docker):
```
docker buildx build  --output ./web/src/whl .
```

Web dev:
```
yarn install
yarn dev
```

`yarn build` may need a larger Node heap: `NODE_OPTIONS=--max-old-space-size=8192`.

Deploying to the NAS behind Tailscale Funnel: see `deploy/deploy.sh`.

### Fancy wizard links
Some example links are provided in web/src/public/examplelink.html
