import csv
import sys
import os
import networkx as nx
from pyvis.network import Network

def parse_airodump_csv(file_path):
    aps = {}
    clients = []

    with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
        lines = f.readlines()

    is_client_section = False

    for line in lines:
        line = line.strip()
        
        if not line or line.startswith('\r') or line.startswith('\n'):
            continue

        if 'Station MAC' in line:
            is_client_section = True
            continue

        parts = [p.strip() for p in line.split(',')]

        if not is_client_section and len(parts) >= 14:
            bssid = parts[0]
            essid = parts[13] if len(parts) > 13 and parts[13] else "<Hidden>"
            if bssid != "BSSID" and len(bssid) == 17:
                aps[bssid] = essid

        elif is_client_section and len(parts) >= 6:
            station_mac = parts[0]
            bssid = parts[5]
            if station_mac != "Station MAC" and bssid != "(not associated)" and len(station_mac) == 17:
                clients.append({'mac': station_mac, 'bssid': bssid})

    return aps, clients

def generate_interactive_graph(aps, clients, output_file="wifi_topology.html"):
    net = Network(height='1000px', width='100%', bgcolor='#1a1a1a', font_color='white', directed=False)
    
    G = nx.Graph()

    # Assegnazione del Livello 1 agli Access Point per il layout gerarchico
    for bssid, essid in aps.items():
        label = f"{essid}\n({bssid})"
        G.add_node(bssid, label=label, title=f"Access Point\nMAC {bssid}", color='#ff4d4d', size=40, level=1)

    # Assegnazione del Livello 2 ai Client
    for client in clients:
        mac = client['mac']
        bssid = client['bssid']

        if mac not in G:
            G.add_node(mac, label=mac, title=f"Client\nMAC {mac}", color='#4da6ff', size=20, level=2)

        if bssid in aps:
            G.add_edge(mac, bssid, color='#666666', width=2)

    net.from_nx(G)
    
    # Iniezione delle opzioni JavaScript per strutturare l'albero visivo
    net.set_options("""
    var options = {
      "layout": {
        "hierarchical": {
          "enabled": true,
          "direction": "UD",
          "sortMethod": "directed",
          "nodeSpacing": 120,
          "treeSpacing": 250,
          "levelSeparation": 200
        }
      },
      "physics": {
        "hierarchicalRepulsion": {
          "centralGravity": 0.0,
          "springLength": 100,
          "springConstant": 0.01,
          "nodeDistance": 150,
          "damping": 0.09
        },
        "solver": "hierarchicalRepulsion"
      }
    }
    """)

    net.save_graph(output_file)
    print(f"Rappresentazione generata con successo e salvata in {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n[!] Errore - Manca il file CSV di airodump")
        print(f"Utilizzo corretto - python {os.path.basename(sys.argv[0])} <nome_file.csv>\n")
        sys.exit(1)
        
    csv_filename = sys.argv[1]
    
    if os.path.exists(csv_filename):
        print("Analisi e riordino della topologia in corso...")
        access_points, associated_clients = parse_airodump_csv(csv_filename)
        generate_interactive_graph(access_points, associated_clients)
    else:
        print(f"Errore - Il file {csv_filename} non è stato trovato")
