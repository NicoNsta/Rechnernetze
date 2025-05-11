import socket
import ssl
import base64
import time

# === Konfiguration ===
SERVER    = 'asmtp.htwg-konstanz.de'
PORT      = 587
USERNAME  = 'rnetin12'
PASSWORD  = 'ju3Oodoo1cah9z'
FROM      = 'nicolas.huhle@htwg-konstanz.de'
TO        = 'nicolas.huhle@htwg-konstanz.de'
SUBJECT   = 'Betreff'
BODY      = 'Guten Tag?\r\nTag okay!\r\n'

TIMEOUT   = 10  # Sekunden

# Hilfsfunktionen, um Send/Receive zu protokollieren
def recv_line(sock):
    data = sock.recv(4096).decode('utf-8', errors='ignore')
    print('<<', data.strip())
    return data

def send_line(sock, line: str):
    print('>>', line.strip())
    sock.send(line.encode('utf-8'))

def main():
    # 1) Plain-TCP-Verbindung aufbauen
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(TIMEOUT)
    client.connect((SERVER, PORT))

    # Server-Banner lesen
    recv_line(client)

    # 2) EHLO
    send_line(client, 'ehlo localhost\r\n')
    recv_line(client)

    # 3) STARTTLS
    send_line(client, 'starttls\r\n')
    recv_line(client)

    # Kurze Pause, damit der Server bereit ist
    time.sleep(1)

    # 4) TLS-Schicht aufsetzen
    context = ssl.create_default_context()
    tls_sock = context.wrap_socket(client, server_hostname=SERVER)

    # Nach dem TLS-Handschlag erneut EHLO
    send_line(tls_sock, 'ehlo localhost\r\n')
    recv_line(tls_sock)

    # 5) AUTH LOGIN
    send_line(tls_sock, 'auth login\r\n')
    recv_line(tls_sock)

    # Benutzername und Passwort in Base64
    user_b64 = base64.b64encode(USERNAME.encode('utf-8')).decode('utf-8')
    pass_b64 = base64.b64encode(PASSWORD.encode('utf-8')).decode('utf-8')

    send_line(tls_sock, user_b64 + '\r\n')
    recv_line(tls_sock)

    send_line(tls_sock, pass_b64 + '\r\n')
    recv_line(tls_sock)

    # 6) MAIL FROM
    send_line(tls_sock, f'mail from:<{FROM}>\r\n')
    recv_line(tls_sock)

    # 7) RCPT TO
    send_line(tls_sock, f'rcpt to:<{TO}>\r\n')
    recv_line(tls_sock)

    # 8) DATA
    send_line(tls_sock, 'data\r\n')
    recv_line(tls_sock)

    # 9) Kopfzeilen und Body, zum Abschluss mit "\r\n.\r\n"
    headers_body = (
        f'Subject: {SUBJECT}\r\n'
        f'From: {FROM}\r\n'
        f'To: {TO}\r\n'
        f'\r\n'
        f'{BODY}'
        f'.\r\n'
    )
    send_line(tls_sock, headers_body)
    recv_line(tls_sock)

    # 10) Beenden
    send_line(tls_sock, 'quit\r\n')
    recv_line(tls_sock)

    tls_sock.close()

if __name__ == '__main__':
    main()
