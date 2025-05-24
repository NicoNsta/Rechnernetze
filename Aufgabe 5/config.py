# Network ports
SERVER_TCP_PORT    = 50000  # Port, auf dem der Server TCP-Verbindungen entgegennimmt
SERVER_UDP_PORT    = 50001  # Port, auf dem der Server UDP-Pakete empfängt

# Nickname
MAX_NICKNAME_LENGTH = 64    # Max. Länge wie im Protokoll

# Socket / Protokoll
RECV_BUFFER_SIZE    = 4096  # Bytes, Buffer für recv()
SOCKET_TIMEOUT      = 5     # Sekunden, Default-Timeout für blocking-Calls

# Protokoll-Antwortcodes
RESPONSE_SUCCESS        = 0x00
RESPONSE_INVALID_FORMAT = 0x01