# client.py
import socket
import threading
import struct
import time
import config
from protocols import (
    pack_register,      # für Registration & Handshake
    unpack_register,    # für Peer-Update & ACK-Paket
    unpack_message,     # für Broadcasts
    REGISTER_FORMAT,
    MESSAGE_HEADER_FORMAT
)
from utils import send_all, recv_exact, send_with_header

peer_list       = {}    # nick → (ip, udp_port)
server_ip       = None
local_ip        = None
local_udp_port  = None
local_tcp_port  = None
server_sock     = None  # TCP für Gruppen-Broadcasts
my_nick         = None

def udp_listener():
    """
    1) P2P-Update (pack_register) → Peer-Liste ergänzen
    2) P2P-Handshake (pack_register) → ACK zurücksenden
    3) Broadcast (pack_message) → anzeigen
    """
    global local_udp_port
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", 0))  # lauscht an allen Interfaces
    local_udp_port = sock.getsockname()[1]
    print(f"UDP-Port (lokal): {local_udp_port}")

    while True:
        data, (ip, port) = sock.recvfrom(config.RECV_BUFFER_SIZE)

        # Versuch: pack_register?
        try:
            p_ip, p_port, p_nick = unpack_register(data)
        except ValueError:
            # kein Register-Paket → Broadcast?
            try:
                ts, msg = unpack_message(data)
                print(f"[{ts}] Broadcast: {msg.decode()}")
            except ValueError:
                pass
            continue

        # Ist Peer-Update oder Handshake?
        if p_nick not in peer_list:
            # Neuer Peer-Update (Server oder erster Kontakt)
            peer_list[p_nick] = (p_ip, p_port)
            print(f"Neuer Peer verfügbar: {p_nick} @ {p_ip}:{p_port}")
        else:
            # Vorher schon bekannt: unterscheide Update vs. Handshake
            stored_ip, stored_udp = peer_list[p_nick]
            if p_port == stored_udp:
                # reines Update, nichts weiter
                continue
            # P2P-Handshake-Anfrage → sende ACK zurück
            ack = pack_register(
                local_ip,
                local_tcp_port,
                my_nick
            )
            # zurück an den Quell-UDP-Port (ip,port)
            sock.sendto(ack, (ip, port))

def p2p_tcp_listener():
    """Hört auf eingehende Private-Chats (TCP)."""
    global local_tcp_port
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("", 0))
    srv.listen()
    local_tcp_port = srv.getsockname()[1]
    print(f"P2P TCP-Port (lokal): {local_tcp_port}")

    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle_p2p_conn, args=(conn,), daemon=True).start()

def handle_p2p_conn(conn: socket.socket):
    """Empfängt Private-Nachrichten auf einer P2P-TCP-Verbindung."""
    try:
        while True:
            hdr = recv_exact(conn, struct.calcsize(MESSAGE_HEADER_FORMAT))
            ts, length = struct.unpack(MESSAGE_HEADER_FORMAT, hdr)
            msg = recv_exact(conn, length).decode()
            print(f"[{ts}] Private: {msg}")
    except Exception:
        print("P2P-Verbindung beendet.")
    finally:
        conn.close()

def tcp_register(nick: str):
    """Registriert beim Server und lädt initiale Peer-Liste."""
    global server_sock, my_nick, local_ip
    my_nick = nick
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.connect((server_ip, config.SERVER_TCP_PORT))
    # lokale IP für P2P ermitteln
    local_ip = server_sock.getsockname()[0]

    pkt = pack_register(local_ip, local_udp_port, nick)
    send_all(server_sock, pkt)
    resp = server_sock.recv(1)
    if not resp or resp[0] != config.RESPONSE_SUCCESS:
        print("Registrierung fehlgeschlagen.")
        return
    print("Registrierung OK.")

    # Peer-Liste: erstes Byte = count
    cnt = server_sock.recv(1)[0]
    for _ in range(cnt):
        hdr = recv_exact(server_sock, struct.calcsize(REGISTER_FORMAT))
        ip2, udp2, nick2 = unpack_register(hdr + recv_exact(server_sock, hdr[-1]))
        peer_list[nick2] = (ip2, udp2)
    print("Peers:", list(peer_list.keys()))

def send_broadcast(msg: str):
    """Sendet Gruppen-Broadcast über TCP an den Server."""
    if not server_sock:
        print("Nicht registriert.")
        return
    send_with_header(server_sock, int(time.time()), msg.encode())

def peer_chat(target: str):
    """
    Initiator:
    1) UDP-Handshake (pack_register mit local_tcp_port)
    2) Auf ACK warten
    3) TCP-Verbindung aufbauen
    4) Private-Chat-Loop
    """
    if target not in peer_list:
        print("Peer nicht bekannt.")
        return
    ip, udp_port = peer_list[target]

    # 1) Handshake senden
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    req = pack_register(local_ip, local_tcp_port, my_nick)
    sock.sendto(req, (ip, udp_port))

    # 2) ACK empfangen
    sock.settimeout(config.SOCKET_TIMEOUT)
    try:
        data, _ = sock.recvfrom(config.RECV_BUFFER_SIZE)
        peer_ip, peer_tcp_port, peer_nick = unpack_register(data)
    except Exception:
        print("Handshake fehlgeschlagen.")
        return
    finally:
        sock.close()

    # 3) TCP-Chat starten
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.connect((peer_ip, peer_tcp_port))
    print(f"P2P-Verbindung zu {peer_nick} @ {peer_ip}:{peer_tcp_port}")
    threading.Thread(target=handle_p2p_conn, args=(conn,), daemon=True).start()

    # 4) Private-Chat-Loop
    while True:
        line = input(f"(privat @{peer_nick})> ")
        if not line:
            break
        send_with_header(conn, int(time.time()), line.encode())
    conn.close()

def main():
    global server_ip
    server_ip = input("Server IP-Adresse: ")
    nick      = input("Nickname: ")
    # Listener starten
    threading.Thread(target=udp_listener,    daemon=True).start()
    threading.Thread(target=p2p_tcp_listener, daemon=True).start()
    time.sleep(0.1)
    tcp_register(nick)
    # Kommando-Loop
    while True:
        cmd = input("> ")
        if cmd.startswith("/bc "):
            send_broadcast(cmd[4:])
        elif cmd.startswith("/chat "):
            peer_chat(cmd.split()[1])

if __name__ == "__main__":
    main()
