import socket
import errno
from threading import Thread
import time

# Ziel und Scan-Parameter
TARGET_IP   = '141.37.168.26'
PORT_START  = 1
PORT_END    = 50
TIMEOUT     = 1.0   # Sekunden

# Flags und Ergebnis-Listen
Continue           = True
open_tcp_ports     = []
udp_responded      = []  # UDP-Ports, die eine Antwort geliefert haben
udp_no_response    = []  # UDP-Ports, bei denen es timeout gab
udp_error_10054    = []  # UDP-Ports, bei denen WinError 10054 auftrat

def scan_tcp_port(port):
    global Continue
    if not Continue:
        return
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(TIMEOUT)
    try:
        sock.connect((TARGET_IP, port))
    except (socket.timeout, ConnectionRefusedError):
        return
    # Port offen
    open_tcp_ports.append(port)
    try:
        sock.send(b'Pingg')
        data = sock.recv(1024)
        print(f'[TCP] Port {port} geantwortet: {data!r}')
    except socket.timeout:
        print(f'[TCP] Port {port} offen, aber keine Antwort innerhalb {TIMEOUT}s')
    except ConnectionResetError:
        print(f'[TCP] Port {port} offen, Verbindung vom Server geschlossen')
    finally:
        sock.close()

def scan_udp_port(port):
    global Continue
    if not Continue:
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)
    try:
        # Mit connect() bekommst du ICMP-Unreachable als ConnectionResetError
        sock.connect((TARGET_IP, port))
        sock.send(b'Pingg')
        data = sock.recv(1024)
    except socket.timeout:
        udp_no_response.append(port)
    except ConnectionResetError as e:
        # WinError 10054 oder errno.ECONNRESET
        udp_error_10054.append(port)
    else:
        udp_responded.append(port)
        print(f'[UDP] Port {port} geantwortet: {data!r}')
    finally:
        sock.close()


def main():
    start = time.time()

    # --- TCP-Scan ---
    print('\n' + '='*10 + ' TCP-Scan Ports 1–50 ' + '='*10)
    tcp_threads = []
    for p in range(PORT_START, PORT_END + 1):
        t = Thread(target=scan_tcp_port, args=(p,))
        t.start()
        tcp_threads.append(t)
    for t in tcp_threads:
        t.join()
    print('\nOffene TCP-Ports:', sorted(open_tcp_ports))

    # --- UDP-Scan ---
    print('\n' + '='*10 + ' UDP-Scan Ports 1–50 ' + '='*10)
    udp_threads = []
    for p in range(PORT_START, PORT_END + 1):
        t = Thread(target=scan_udp_port, args=(p,))
        t.start()
        udp_threads.append(t)
    for t in udp_threads:
        t.join()

    # UDP-Ergebnisse
    print('\nUDP-Ports mit Antwort:', sorted(udp_responded))
    print('UDP-Ports ohne Antwort (Timeout):', sorted(udp_no_response))
    print('UDP-Ports mit ICMP “Port Unreachable” (WinError 10054):', sorted(udp_error_10054))

    # Gesamtdauer
    print(f'\nDauer insgesamt: {time.time() - start:.2f}s')

if __name__ == '__main__':
    main()
