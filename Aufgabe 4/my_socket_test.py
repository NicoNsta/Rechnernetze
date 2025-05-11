import socket
socket.setdefaulttimeout(30)

My_IP = '127.0.0.1'
My_PORT = 50000
Remote_IP = '127.0.0.2'
Remote_PORT = 50000

def start_task(sock, message):
    sock.send(message.encode('utf-8'))
    msg = sock.recv(1024)
    sock.close()

def start_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((My_IP, My_PORT))
    sock.listen(1)
    try:
        conn, addr = sock.accept()
        start_task(conn, "Thx for connecting!!!")
    except socket.timeout:
        pass

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    sock.connect((Remote_IP, Remote_PORT))
    start_task(sock, "Thx for accepting!!!")
except socket.error:
    start_server()
