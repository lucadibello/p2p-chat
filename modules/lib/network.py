from socket import socket
from gen.proto.communication_pb2 import (
    PeerMessage,
)

from modules.model.routing_table import RoutingTable
from modules.lib.logger import Logger


def send(conn: socket, msg: PeerMessage) -> None:
    serialized = msg.SerializeToString()
    conn.sendall(len(serialized).to_bytes(4, byteorder="big"))
    conn.sendall(serialized)


def receive(conn: socket) -> PeerMessage:
    msg = PeerMessage()
    size_data = conn.recv(4)
    if not size_data:
        raise ConnectionResetError("Connection closed by peer during size reception")

    size = int.from_bytes(size_data, byteorder="big")
    data = conn.recv(size)
    if len(data) < size:
        raise ConnectionResetError("Incomplete message received")

    msg.ParseFromString(data)
    return msg


def send_broadcast(routing_table: RoutingTable, msg: PeerMessage) -> None:
    for _, (conn, _) in routing_table:
        if conn is None:
            continue
        # Otherwise, send the message to the peer
        send(conn, msg)
