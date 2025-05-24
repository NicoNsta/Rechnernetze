# protocols.py
import struct
import socket  # IP-Konvertierung
from typing import Tuple

# Protokoll-Formate
REGISTER_FORMAT = "<4sHB"        # IP (4s), UDP-Port (H), Nickname-Länge (B)
MESSAGE_HEADER_FORMAT = "<iH"     # Timestamp (i), Länge (H)

# Maximale Nickname-Länge
MAX_NICKNAME_LENGTH = 64

# Antwortcodes
RESPONSE_SUCCESS = 0x00
RESPONSE_INVALID_FORMAT = 0x01


def pack_register(ip: str, udp_port: int, nickname: str) -> bytes:
    """
    Packt IP, UDP-Port und Nickname gemäß REGISTER_FORMAT.
    """
    ip_packed = socket.inet_aton(ip)
    nick_bytes = nickname.encode("utf-8")
    nick_len = len(nick_bytes)
    if nick_len > MAX_NICKNAME_LENGTH:
        raise ValueError(f"Nickname zu lang (max {MAX_NICKNAME_LENGTH}): {nick_len}")
    header = struct.pack(REGISTER_FORMAT, ip_packed, udp_port, nick_len)
    return header + nick_bytes


def unpack_register(data: bytes) -> Tuple[str, int, str]:
    """
    Entpackt Registration-Paket und gibt (ip, udp_port, nickname) zurück.
    """
    hdr_size = struct.calcsize(REGISTER_FORMAT)
    if len(data) < hdr_size:
        raise ValueError("Zu wenig Daten im Registration-Header")
    ip_packed, udp_port, nick_len = struct.unpack(REGISTER_FORMAT, data[:hdr_size])
    if len(data) < hdr_size + nick_len:
        raise ValueError("Zu wenig Daten für Nickname")
    nickname = data[hdr_size:hdr_size + nick_len].decode("utf-8")
    ip = socket.inet_ntoa(ip_packed)
    return ip, udp_port, nickname


def pack_message(timestamp: int, msg: bytes) -> bytes:
    """
    Packt Timestamp und Payload gemäß MESSAGE_HEADER_FORMAT.
    """
    header = struct.pack(MESSAGE_HEADER_FORMAT, timestamp, len(msg))
    return header + msg


def unpack_message(data: bytes) -> Tuple[int, bytes]:
    """
    Entpackt Header+Payload und gibt (timestamp, msg) zurück.
    """
    hdr_size = struct.calcsize(MESSAGE_HEADER_FORMAT)
    if len(data) < hdr_size:
        raise ValueError("Zu wenig Daten im Message-Header")
    timestamp, length = struct.unpack(MESSAGE_HEADER_FORMAT, data[:hdr_size])
    if len(data) < hdr_size + length:
        raise ValueError("Zu wenig Daten für Payload")
    payload = data[hdr_size:hdr_size + length]
    return timestamp, payload