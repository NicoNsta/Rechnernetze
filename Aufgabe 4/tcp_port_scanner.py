import socket
from threading import Thread
import time


TARGET_IP = '141.37.168.26'    # Labor-Server
PORT_START = 1
PORT_END   = 50
TIMEOUT    = 1.0               # Sekunden
Continue   = True              # Abbruch-Flag für Threads
open_ports = []                # Ergebnisliste


import socket

def scan_port(port):
    global Continue
    if not Continue:
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(TIMEOUT)
    try:
        sock.connect((TARGET_IP, port))
    except (socket.timeout, ConnectionRefusedError):
        # Port geschlossen oder keine Antwort
        return

    # Port offen:
    open_ports.append(port)
    try:
        # Nachricht schicken
        sock.send(b'Ping')
        # Erstes Datenpaket abholen (puffere bis zu 1024 Bytes)
        data = sock.recv(1024)
        print(f'Port {port} geantwortet: {data!r}')
    except socket.timeout:
        print(f'Port {port} offen, aber keine Antwort innerhalb {TIMEOUT}s')
    except ConnectionResetError:
        # Server hat Verbindung nach send/recv zurückgesetzt → einfach ignorieren
        print(f'Port {port} offen, Verbindung vom Server geschlossen')
    finally:
        sock.close()




def main():
    threads = []
    # Für jeden Port einen Thread starten
    for port in range(PORT_START, PORT_END + 1):
        t = Thread(target=scan_port, args=(port,))
        t.start()
        threads.append(t)
    # Warten, bis alle Threads fertig sind
    for t in threads:
        t.join()
    # Threads beenden (optional, da sie sich nach einem Versuch selbst beenden)
    global Continue
    Continue = False

    # Ergebnis ausgeben
    print('Offene TCP-Ports:', sorted(open_ports))

if __name__ == '__main__':
    start = time.time()
    main()
    print(f'Dauer: {time.time() - start:.2f}s')
