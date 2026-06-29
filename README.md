<div align="center">
  <img src="wifihound/web/static/img/logo-wordmark.png" alt="WiFiHound" width="440"/>
</div>

WiFiHound turns `airodump-ng` output into an explorable graph of access points,
clients and their associations. Import a past scan and replay it, or run a live
capture and watch the map build in real time.

## Features

* Graph UI with access points in red, clients in blue, associations as edges.
* Search and filters by type, encryption and channel.
* Offline vendor lookup from the OUI database.
* Two ways to build the map: replay an imported capture, or live capture a real
  `airodump-ng` stream.
* WPA2-Enterprise: flag 802.1X APs, inspect the RADIUS certificate, and
  enumerate the EAP methods a network accepts.

## Install

WiFiHound needs Python 3.8 or newer, so use `python3` and `pip3` (a bare `pip`
on an old system can still point at Python 2).

```bash
git clone https://github.com/0xPR3ST1JH0NN7/WiFiHound
cd WiFiHound
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

WiFiHound also needs a few command-line tools on your `PATH`. On startup it
prints a dependency checklist and **refuses to start if a required tool is
missing**:

| Tool | Used for | Required |
| --- | --- | --- |
| `aircrack-ng`, `airmon-ng`, `airodump-ng`, `aireplay-ng` | the aircrack-ng suite — live capture, monitor mode, deauth | ✅ |
| `tshark` | handshake detection + RADIUS certificate extraction | ✅ |
| `wpa_supplicant` | EAP method enumeration | optional |
| `pcapFilter.sh` | faster RADIUS cert extraction (falls back to `tshark`) | optional |
| `EAP_buster.sh` | EAP method enumeration (path via `WIFIHOUND_EAP_BUSTER`) | optional |

```bash
sudo apt install aircrack-ng tshark wpasupplicant
```

Pass `--skip-checks` to bypass the gate for offline-only use (importing and
replaying captures needs no external tools).

## Run

```bash
python3 -m wifihound        # opens http://127.0.0.1:8000
sudo python3 -m wifihound   # also enables live radio capture
python3 -m wifihound stop   # stop a running server gracefully (no Ctrl+C)
```

Click **Import capture** and pick an `airodump-ng` CSV
(`airodump-ng -w scan --output-format csv wlan0mon`).

## Replay

Importing a capture gives you the full graph of a past scan. In the **Replay**
panel press **Replay capture** to watch it rebuild node by node, as if it were
being discovered live. It runs fully offline, with no radio and no root.

![Replay in action](docs/replay.gif)

## Live capture

The **Live capture** panel streams a real `airodump-ng` capture and maps the
network as it appears. It needs root, so run with `sudo`. Pick a wireless
interface from the list of detected adapters; a managed one is switched to
monitor mode automatically and restored when you stop. You can also set a
channel, protocol, WPS and an ESSID or BSSID filter.

![Live capture in action](docs/live-capture.gif)

> Use WiFiHound only on networks you own or are authorized to test.

## Authors

* [@0xPR3ST1JH0NN7](https://github.com/0xPR3ST1JH0NN7)
* [@tvasari](https://github.com/tvasari)
