"""Tests for the connection between two computers: messages in, messages out, and lines that are not messages."""

import net


def pair():
    """Two connected ends over TCP on this computer, like a host and the computer that joined it."""
    host = net.Host(0)
    joined = net.connect("127.0.0.1", host.port)
    accepted = None
    for _ in range(200):
        accepted = host.accept()
        if accepted is not None:
            break
    host.close()
    return joined, accepted


def arrived(connection, tries=50):
    messages = []
    for _ in range(tries):
        messages += connection.poll()
        if messages:
            break
    return messages


def test_a_message_arrives_whole():
    one, other = pair()
    one.send({"t": "sync", "player": {"pos": [1, 2]}})
    assert arrived(other) == [{"t": "sync", "player": {"pos": [1, 2]}}]
    one.close()
    other.close()


def test_broken_or_hostile_lines_are_skipped_and_the_connection_goes_on():
    one, other = pair()
    deep = b"[" * 100_000 + b"]" * 100_000  # deeper than Python can read: it must not crash the game
    for line in (b"not json", b"[1, 2]", b'"text"', deep, b"{" + b" " * (net.MAX_LINE + 10) + b"}"):
        one.sock.sendall(line + b"\n")
    one.send({"t": "ok"})
    messages = []
    for _ in range(200):
        messages += other.poll()
        if {"t": "ok"} in messages:
            break
    assert messages == [{"t": "ok"}] and not other.closed  # only the real message; still connected
    one.close()
    other.close()


def test_a_line_that_never_ends_closes_the_connection():
    one, other = pair()
    one.sock.sendall(b"x" * (net.MAX_LINE + 70_000))
    for _ in range(200):
        other.poll()
        if other.closed:
            break
    assert other.closed
    one.close()
