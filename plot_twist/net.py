"""Two computers on the same network: the connection between them, and nothing else.

One computer hosts the game (Host); the other joins it (connect) by typing the
host's address. They talk in messages: small dicts sent as one line of JSON each.
Everything here is non-blocking: poll() returns the messages that have arrived
so far, and never waits, so the game keeps running at its usual speed.

The game itself (who sends what, and when) is in main.py. This module knows
nothing about pygame or the rules: only sockets, the standard library's.
"""

import json
import socket

PORT = 50555           # where the host waits for the other computer
CONNECT_TIMEOUT = 3    # seconds to wait for the host when joining
MAX_LINE = 1_000_000   # a message longer than this is a broken connection, not a message


class Connection:
    """One end of a connection: send() messages, poll() for the ones that came in."""

    def __init__(self, sock):
        sock.setblocking(False)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # small messages go out at once
        self.sock = sock
        self.incoming = b""
        self.outgoing = b""
        self.closed = False

    def send(self, message):
        """Queue a message and send as much as the network takes now; the rest goes with the next call."""
        if self.closed:
            return
        self.outgoing += json.dumps(message, separators=(",", ":")).encode() + b"\n"
        self.flush()

    def flush(self):
        while self.outgoing and not self.closed:
            try:
                sent = self.sock.send(self.outgoing)
            except BlockingIOError:
                return
            except OSError:
                self.close()
                return
            self.outgoing = self.outgoing[sent:]

    def poll(self):
        """The messages that have arrived since the last call, oldest first. Never waits."""
        self.flush()
        while not self.closed:
            try:
                data = self.sock.recv(65536)
            except BlockingIOError:
                break
            except OSError:
                self.close()
                break
            if not data:  # the other computer closed the connection
                self.close()
                break
            self.incoming += data
            if len(self.incoming) > MAX_LINE and b"\n" not in self.incoming:
                self.close()
        messages = []
        while b"\n" in self.incoming:
            line, self.incoming = self.incoming.split(b"\n", 1)
            if len(line) > MAX_LINE:
                continue  # far too long to be one of ours: skip it
            try:
                message = json.loads(line)
            except (ValueError, RecursionError):
                continue  # a broken line, or nested too deep to read: skip it
            if isinstance(message, dict):
                messages.append(message)
        return messages

    def close(self):
        if not self.closed:
            self.closed = True
            try:
                self.sock.close()
            except OSError:
                pass


class Host:
    """The computer that hosts the game, waiting for the other one to join."""

    def __init__(self, port=PORT):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("", port))
        self.server.listen(1)
        self.server.setblocking(False)
        self.port = self.server.getsockname()[1]  # the real one, if port 0 asked for any free port

    def accept(self):
        """The connection of the computer that just joined, or None if nobody has yet. Never waits."""
        try:
            sock, _ = self.server.accept()
        except (BlockingIOError, OSError):
            return None
        return Connection(sock)

    def close(self):
        try:
            self.server.close()
        except OSError:
            pass


def connect(address, port=PORT, timeout=CONNECT_TIMEOUT):
    """Join the game hosted at `address`. Raises OSError if nobody answers there."""
    sock = socket.create_connection((address, port), timeout=timeout)
    return Connection(sock)


def local_address():
    """This computer's address on the local network, to tell the other player.

    Asking the system how it would reach an outside address sends nothing, but
    tells which network card (and address) it would use.
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 1))
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()
