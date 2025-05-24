# utils.py
import socket
import struct
from typing import Tuple
from protocols import MESSAGE_HEADER_FORMAT, pack_message


def send_all(sock: socket.socket, data: bytes) -> None:
    total_sent = 0
    while total_sent < len(data):
        sent = sock.send(data[total_sent:])
        if sent == 0:
            raise RuntimeError("Socket-Verbindung unterbrochen")
        total_sent += sent


def recv_exact(sock: socket.socket, n: int) -> bytes:
    chunks = []
    bytes_recd = 0
    while bytes_recd < n:
        chunk = sock.recv(n - bytes_recd)
        if not chunk:
            raise RuntimeError("Socket-Verbindung unterbrochen")
        chunks.append(chunk)
        bytes_recd += len(chunk)
    return b"".join(chunks)


def send_with_header(sock: socket.socket, timestamp: int, msg: bytes) -> None:
    packet = pack_message(timestamp, msg)
    send_all(sock, packet)


def recv_with_header(sock: socket.socket) -> Tuple[int, bytes]:
    hdr_size = struct.calcsize(MESSAGE_HEADER_FORMAT)
    raw_hdr = recv_exact(sock, hdr_size)
    timestamp, length = struct.unpack(MESSAGE_HEADER_FORMAT, raw_hdr)
    payload = recv_exact(sock, length)
    return timestamp, payload