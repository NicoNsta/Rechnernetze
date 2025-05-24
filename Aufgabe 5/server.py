# server.py
import socket
import threading
import struct
import config
from protocols import (
    unpack_register,   # für Registration/Handshake
    pack_register,     # für Peer-List-Verteilung
    pack_message,      # für Broadcast
    REGISTER_FORMAT,
    MESSAGE_HEADER_FORMAT
)
from utils import recv_exact, send_all

peers = {}  # nick → (ip, udp_port)
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def handle_client(conn: socket.socket, _addr):
    """
    1) Liest Registration (REGISTER_FORMAT).
    2) Speichert Peer, sendet ACK.
    3) Sendet initiale Peer-Liste per TCP.
    4) Informiert alle bestehenden Peers per UDP (Peer-Update).
    5) Broadcast-Loop: verteilt Chat-Messages via UDP.
    """
    try:
        hdr = recv_exact(conn, struct.calcsize(REGISTER_FORMAT))
        ip, udp_port, nick = unpack_register(hdr + recv_exact(conn, hdr[-1]))
    except Exception:
        conn.send(bytes([config.RESPONSE_INVALID_FORMAT]))
        conn.close()
        return

    # Peer hinzufügen und ACK
    peers[nick] = (ip, udp_port)
    conn.send(bytes([config.RESPONSE_SUCCESS]))
    print(f"Neuer Peer: {nick} @ {ip}:{udp_port}")

    # 3) Initiale Peer-Liste senden
    count = len(peers) - 1
    send_all(conn, bytes([count]))
    for other, (oip, oudp) in peers.items():
        if other == nick: continue
        pkt = pack_register(oip, oudp, other)
        send_all(conn, pkt)

    # 4) Alle bestehenden Peers per UDP über neuen Peer informieren
    update_pkt = pack_register(ip, udp_port, nick)
    for other, (oip, oudp) in peers.items():
        if other == nick: continue
        udp_sock.sendto(update_pkt, (oip, oudp))

    # 5) Broadcast-Loop
    while True:
        try:
            hdr = recv_exact(conn, struct.calcsize(MESSAGE_HEADER_FORMAT))
            ts, length = struct.unpack(MESSAGE_HEADER_FORMAT, hdr)
            msg = recv_exact(conn, length)
        except Exception:
            print(f"Verbindung zu {nick} getrennt.")
            del peers[nick]
            conn.close()
            break

        packet = pack_message(ts, msg)
        for other, (oip, oudp) in peers.items():
            if other == nick: continue
            udp_sock.sendto(packet, (oip, oudp))

def tcp_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", config.SERVER_TCP_PORT))  # hört an allen Interfaces
    s.listen()
    print(f"TCP-Server läuft auf Port {config.SERVER_TCP_PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

def udp_listener():
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    u.bind(("", config.SERVER_UDP_PORT))
    print(f"UDP-Listener läuft auf Port {config.SERVER_UDP_PORT}")
    # Server ignoriert hier P2P-Handshake; Clients handhaben ihn selbst
    while True:
        u.recvfrom(config.RECV_BUFFER_SIZE)

if __name__ == "__main__":
    threading.Thread(target=tcp_server, daemon=True).start()
    udp_listener()
