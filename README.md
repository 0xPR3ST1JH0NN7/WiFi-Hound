<div align="center">
  <img src="wifihound/web/static/img/logo.svg" alt="WiFiHound" width="140"/>

  # WiFiHound

  **Interactive graph analysis for WiFi reconnaissance data.**

  Turn an `airodump-ng` capture into a live, explorable map of access points,
  clients and their associations, then search, filter and pivot through it in
  the browser.
</div>

---

## What it does

WiFiHound ingests WiFi scan data and renders it as an interactive node graph.
Instead of staring at CSV rows, you get a topology you can **explore**:

- **Access Points** (red) and **Clients** (blue) as nodes, associations as edges.
- **Search** by ESSID, BSSID, MAC or vendor and jump straight to the node.
- **Click a node** for a full details panel (channel, encryption, cipher, signal,
  vendor, first and last seen, probed ESSIDs).
- **Filter** by node type, encryption, channel, or association state.
- **Right click** a node for actions (highlight neighbors, isolate subgraph,
  copy identifier).
- **Vendor enrichment** from the OUI (offline, no setup required).
- Multiple **layouts** (force, hierarchical, concentric, circle, grid).
- **Live capture**: watch the graph build in real time, either by replaying a
  loaded CSV or by streaming a real airodump-ng capture over WebSocket.

It is built around a small **web app** (a local FastAPI server plus a Cytoscape.js
frontend with no build step) because real interactivity, namely clicking,
searching and pivoting, is exactly what a static export can't give you.

## Architecture

```
wifihound/
├── cli.py              # `python -m wifihound serve`
├── server.py           # FastAPI app + static frontend
├── models.py           # AccessPoint / Client / Scan data model
├── graph.py            # networkx graph: search, neighbors, paths, Cytoscape JSON
├── parsers/            # pluggable capture parsers (airodump CSV today)
├── enrichment/         # OUI vendor lookup + geo hook
├── operations/         # offensive ops (guardrailed, opt in)
├── capture/            # live capture: sources + controller (replay / airodump)
├── api/routes.py       # REST API + live WebSocket
└── web/                # index.html + Cytoscape.js UI (vendored, offline)
```

Adding a new input format is a matter of dropping a `Parser` subclass into
`wifihound/parsers/` and registering it. Kismet (`netxml`/`.kismet`), raw
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
# -> produces scan-01.csv, which you import into WiFiHound
```

Useful flags:

```bash
python -m wifihound serve --port 9000        # custom port
python -m wifihound serve --no-browser       # don't auto open a browser
python -m wifihound serve --reload           # dev auto reload
```

### Better vendor resolution

A compact OUI table ships built in. For full coverage, point WiFiHound at a
Wireshark style `manuf` / IEEE OUI file:

```bash
WIFIHOUND_OUI_FILE=/usr/share/wireshark/manuf python -m wifihound serve
```

## Live capture

WiFiHound works both ways: analyze a capture after the fact, or watch the graph
build in real time. Open the **Live capture** panel in the sidebar:

- **Replay** (no privileges): import a CSV, then **Start live** to watch that
  same capture reveal itself node by node. Great for demos and for reviewing how
  a network populated. Works on any machine, no hardware needed.
- **airodump (live radio)**: stream a real `airodump-ng` capture. The backend
  spawns airodump-ng, tails its rotating CSV, and pushes incremental graph
  updates to the browser over a WebSocket. This touches radio hardware, so it
  carries the **same guardrails as the offensive operations**: start the server
  with `--enable-offensive`, run as **root**, and provide a monitor-mode
  interface.

Offline import stays the default and needs no privileges; live capture is an
opt-in layer on top.

## Offensive operations (authorized testing only)

WiFiHound can drive active operations such as **deauthentication** (e.g. to
capture a WPA handshake during an authorized assessment) via the `aircrack-ng`
suite. These are **off by default** and protected by multiple guardrails:

- enabled only with an explicit flag: `sudo python -m wifihound serve --enable-offensive`
- require **root** and the `aircrack-ng` tools to be installed
- require a confirmation in the UI for every action
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
offensive operation guardrails. The frontend dependencies (Cytoscape.js and
extensions) are vendored under `wifihound/web/static/vendor/`, so the tool runs
fully offline with no Node toolchain.

## Roadmap

- Additional parsers: Kismet `netxml`/`.kismet`, `pcap`/`.cap`, native JSON.
- Probe request edges (clients to searched ESSIDs) to surface "evil twin" pivots.
- Saved sessions and graph export (PNG / JSON).
- Geolocation overlay for captures tagged with GPS.

## License

See the repository for license details.
