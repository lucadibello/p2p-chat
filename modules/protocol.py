from gen.proto.communication_pb2 import HandshakeStart, HandshakeAck
from modules.communication import send_message, receive_message
from modules.snowflake import derive_id
from random import randint
from typing import Callable


def generate_peer_id() -> int:
    def generate_id(length: int = 17) -> int:
        return int("".join([str(randint(0, 9)) for _ in range(length)]))

    # use snowflake IDs
    return derive_id(generate_id())


def perform_handshake(
    conn,
    chosen_id: int,
) -> tuple[bool, int]:
    print("Performing handshake...")
    handshake = HandshakeStart(id=chosen_id)

    # Send the handshake message
    send_message(conn, handshake)

    # Receive the handshake ack
    ack = receive_message(conn, HandshakeAck)
    if not ack.error and ack.id == chosen_id:
        return True, chosen_id
    return False, ack.id
