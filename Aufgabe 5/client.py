# client.py
import socket
import threading
import struct
import time
import config
from protocols import (
    pack_register,
    unpack_register,
    unpack_message,
    REGISTER_FORMAT,
    MESSAGE_HEADER_FORMAT
)
from utils import send_all, recv_exact, send_with_header

# Lock für synchronisierte Konsolenausgaben
print_lock = threading.Lock()

peer_list       = {}    # nick → (ip, udp_port)
server_ip       = None
local_ip        = None
local_udp_port  = None
local_tcp_port  = None
server_sock     = None  # TCP für Gruppen-Broadcasts
my_nick         = None


def udp_listener():
    """
    Lauscht auf UDP für:
      a) Peer-Updates (pack_register) → Peer-Liste ergänzen
      b) Handshake-Anfragen → ACK zurücksenden
      c) Gruppen-Broadcasts (pack_message) → anzeigen
    """
    global local_udp_port
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", 0))  # hört an allen Interfaces
    local_udp_port = sock.getsockname()[1]
    with print_lock:
        print(f"UDP-Port (lokal): {local_udp_port}")

    while True:
        data, (ip, port) = sock.recvfrom(config.RECV_BUFFER_SIZE)

        # Versuch: ist es ein Peer-Update oder Handshake-Paket?
        try:
            p_ip, p_port, p_nick = unpack_register(data)
        except ValueError:
            # Kein Register-Paket, daher Broadcast?
            try:
                ts, msg = unpack_message(data)
                with print_lock:
                    print(f"\n[{ts}] Broadcast: {msg.decode()}")
            except ValueError:
                pass
            continue

        # Peer-Update oder Handshake unterscheiden
        if p_nick not in peer_list:
            # Neuer Peer-Update
            peer_list[p_nick] = (p_ip, p_port)
            with print_lock:
                print(f"\nNeuer Peer verfügbar: {p_nick} @ {p_ip}:{p_port}")
        else:
            # Bereits bekannter Peer: Handshake prüfen
            stored_ip, stored_udp = peer_list[p_nick]
            if p_port == stored_udp:
                # nur Update
                continue
            # Handshake-Anfrage: ACK senden
            # Benachrichtigung an den Empfänger
            with print_lock:
                print(f"\n{p_nick} hat einen P2P-Chat mit Ihnen gestartet")
            ack = pack_register(local_ip, local_tcp_port, my_nick)
            sock.sendto(ack, (ip, port))


def p2p_tcp_listener():
    """
    Hört auf eingehende Private-Chats (TCP).
    """
    global local_tcp_port
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("", 0))
    srv.listen()
    local_tcp_port = srv.getsockname()[1]
    with print_lock:
        print(f"P2P TCP-Port (lokal): {local_tcp_port}")

    while True:
        conn, addr = srv.accept()
        # Ermitteln des Peer-Nicks anhand der IP
        peer_ip, _ = addr
        peer_nick = next((nick for nick,(ip,_) in peer_list.items() if ip == peer_ip), peer_ip)
        threading.Thread(target=handle_p2p_conn, args=(conn, peer_nick), daemon=True).start()


def handle_p2p_conn(conn: socket.socket, peer_nick: str):
    """
    Empfängt Private-Nachrichten und zeigt sie mit Peer-Nick an.
    """
    try:
        while True:
            hdr = recv_exact(conn, struct.calcsize(MESSAGE_HEADER_FORMAT))
            ts, length = struct.unpack(MESSAGE_HEADER_FORMAT, hdr)
            msg = recv_exact(conn, length).decode()
            with print_lock:
                print(f"\n[{ts}] Private von {peer_nick}: {msg}")
    except Exception:
        with print_lock:
            print(f"\nP2P-Verbindung zu {peer_nick} beendet.")
    finally:
        conn.close()


def tcp_register(nick: str):
    """
    Registriert beim Server und lädt initiale Peer-Liste.
    """
    global server_sock, my_nick, local_ip
    my_nick = nick
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_sock.connect((server_ip, config.SERVER_TCP_PORT))
    except socket.gaierror:
        with print_lock:
            print("Ungültige Server-IP. Bitte prüfen und neu starten.")
        exit(1)
    except Exception as e:
        with print_lock:
            print(f"Verbindung zum Server fehlgeschlagen: {e}")
        exit(1)

    local_ip = server_sock.getsockname()[0]
    pkt = pack_register(local_ip, local_udp_port, nick)
    send_all(server_sock, pkt)

    resp = server_sock.recv(1)
    if not resp or resp[0] != config.RESPONSE_SUCCESS:
        with print_lock:
            print("Registrierung fehlgeschlagen.")
        exit(1)
    with print_lock:
        print("Registrierung OK.")

    cnt = server_sock.recv(1)[0]
    for _ in range(cnt):
        hdr = recv_exact(server_sock, struct.calcsize(REGISTER_FORMAT))
        ip2, udp2, nick2 = unpack_register(hdr + recv_exact(server_sock, hdr[-1]))
        peer_list[nick2] = (ip2, udp2)
    with print_lock:
        print("Peers:", list(peer_list.keys()))


def send_broadcast(msg: str):
    if not server_sock:
        with print_lock:
            print("Nicht registriert.")
        return
    send_with_header(server_sock, int(time.time()), msg.encode())


def peer_chat(target: str):
    """
    Initiiert P2P-Chat (Handshake → TCP → Chat).
    """
    if target not in peer_list:
        with print_lock:
            print("Peer nicht bekannt.")
        return
    ip, udp_port = peer_list[target]

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    req = pack_register(local_ip, local_tcp_port, my_nick)
    sock.sendto(req, (ip, udp_port))
    sock.settimeout(config.SOCKET_TIMEOUT)
    try:
        data, _ = sock.recvfrom(config.RECV_BUFFER_SIZE)
        peer_ip, peer_tcp_port, peer_nick = unpack_register(data)
    except Exception:
        with print_lock:
            print("Handshake fehlgeschlagen.")
        sock.close()
        return
    sock.close()

    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.connect((peer_ip, peer_tcp_port))
    with print_lock:
        print(f"P2P-Verbindung zu {peer_nick} @ {peer_ip}:{peer_tcp_port}")
    threading.Thread(target=handle_p2p_conn, args=(conn, peer_nick), daemon=True).start()

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

    threading.Thread(target=udp_listener,    daemon=True).start()
    threading.Thread(target=p2p_tcp_listener, daemon=True).start()
    time.sleep(0.1)
    tcp_register(nick)

    while True:
        cmd = input("> ")
        if cmd.startswith("/bc "):
            send_broadcast(cmd[4:])
        elif cmd.startswith("/chat "):
            peer_chat(cmd.split()[1])

if __name__ == "__main__":
    main()
