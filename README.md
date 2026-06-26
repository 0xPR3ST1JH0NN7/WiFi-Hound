<div align="center">
  <img src="wifihound/web/static/img/logo.svg" alt="WiFi-Hound" width="140"/>

  # WiFi-Hound

  **Interactive graph analysis for Wi-Fi reconnaissance data.**

  Turn an `airodump-ng` capture into a live, explorable map of access points,
  clients and their associations — then search, filter and pivot through it in
  the browser.
</div>

---

## What it does

WiFi-Hound ingests Wi-Fi scan data and renders it as an interactive node graph.
Instead of staring at CSV rows, you get a topology you can **explore**:

- **Access Points** (red) and **Clients** (blue) as nodes, associations as edges.
- **Search** by ESSID, BSSID, MAC or vendor and jump straight to the node.
- **Click a node** for a full details panel (channel, encryption, cipher, signal,
  vendor, first/last seen, probed ESSIDs…).
- **Filter** by node type, encryption, channel, or association state.
- **Right-click** a node for actions (highlight neighbors, isolate subgraph,
  copy identifier).
- **Vendor enrichment** from the OUI (offline, no setup required).
- Multiple **layouts** (force / hierarchical / concentric / circle / grid).

It is built around a small **web app** (a local FastAPI server + a zero-build
Cytoscape.js frontend) because real interactivity — clicking, searching,
pivoting — is exactly what a static export can't give you.

## Architecture

```
wifihound/
├── cli.py              # `python -m wifihound serve`
├── server.py           # FastAPI app + static frontend
├── models.py           # AccessPoint / Client / Scan data model
├── graph.py            # networkx graph: search, neighbors, paths, Cytoscape JSON
├── parsers/            # pluggable capture parsers (airodump CSV today)
├── enrichment/         # OUI vendor lookup + geo hook
├── operations/         # offensive ops (guardrailed, opt-in)
├── api/routes.py       # REST API
└── web/                # index.html + Cytoscape.js UI (vendored, offline)
```

Adding a new input format is a matter of dropping a `Parser` subclass into
`wifihound/parsers/` and registering it — Kismet (`netxml`/`.kismet`), raw
`pcap`/`.cap`, and a native JSON format are the natural next additions.

## Install

Requires Python 3.10+.

```bash
git clone https://github.com/0xPR3ST1JH0NN7/WiFi-Hound
cd WiFi-Hound
pip install -r requirements.txt
```

## Usage

```bash
python -m wifihound serve
```

This starts the app on <http://127.0.0.1:8000> and opens your browser.
Click **Import capture** and choose an `airodump-ng` CSV.

Generate a capture with airodump-ng:

```bash
# put your interface into monitor mode first (e.g. with airmon-ng)
airodump-ng -w scan --output-format csv wlan0mon
# -> produces scan-01.csv, which you import into WiFi-Hound
```

Useful flags:

```bash
python -m wifihound serve --port 9000        # custom port
python -m wifihound serve --no-browser       # don't auto-open a browser
python -m wifihound serve --reload           # dev auto-reload
```

### Better vendor resolution

A compact OUI table ships built-in. For full coverage, point WiFi-Hound at a
Wireshark-style `manuf` / IEEE OUI file:

```bash
WIFIHOUND_OUI_FILE=/usr/share/wireshark/manuf python -m wifihound serve
```

## Offensive operations (authorized testing only)

WiFi-Hound can drive active operations such as **deauthentication** (e.g. to
capture a WPA handshake during an authorized assessment) via the `aircrack-ng`
suite. These are **off by default** and protected by multiple guardrails:

- enabled only with an explicit flag: `sudo python -m wifihound serve --enable-offensive`
- require **root** and the `aircrack-ng` tools to be installed
- require a per-action confirmation in the UI
- burst counts are capped, and every action is logged

> ⚠️ **Use only on networks you own or are explicitly authorized in writing to
> test.** Sending deauthentication frames to, or intercepting traffic of,
> networks you do not control is illegal in most jurisdictions. This subsystem
> exists for legitimate, authorized penetration testing and security research.

## Development

```bash
pip install -r requirements.txt
pytest                      # run the test suite
python -m wifihound serve --reload
```

Tests cover the airodump parser, the graph model, the REST API, and the
offensive-operation guardrails. The frontend dependencies (Cytoscape.js and
extensions) are vendored under `wifihound/web/static/vendor/`, so the tool runs
fully offline with no Node toolchain.

## Roadmap

- Additional parsers: Kismet `netxml`/`.kismet`, `pcap`/`.cap`, native JSON.
- Probe-request edges (clients → searched ESSIDs) to surface "evil-twin" pivots.
- Saved sessions and graph export (PNG / JSON).
- Geolocation overlay for GPS-tagged captures.

## License

See the repository for license details.
