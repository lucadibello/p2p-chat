import socket
from random import randint
from threading import Event
from typing import Optional

from gen.proto.communication_pb2 import (
    AnnouncementType,
    HandshakeResponse,
    HandshakeStart,
    PeerMessage,
    PeerMessageType,
)
from modules.lib.logger import Logger
from modules.lib.network import receive, send
from modules.lib.snowflake import derive_id
from modules.model.errors import NoRouteError
from modules.model.routing_table import RoutingTable


class Peer:
    _ID: Optional[int] = None
    EXIT_EVENT = Event()
    logger = Logger("p2p-network").get_logger()
    routing_table = RoutingTable()
    buffer = dict[int, list[PeerMessage]]()

    @staticmethod
    def handle_handshake(conn: socket.socket) -> tuple[int, bool]:
        # Receive the handshake message
        handshake = receive(conn)
        if handshake.type != PeerMessageType.HANDSHAKE_START:
            raise ConnectionError(
                f"[ServerWorker] Unexpected message type received during handshake: expected {PeerMessageType.HANDSHAKE_START}, got {handshake.type}"
            )
        handshake = handshake.handshakeStart
        # Ensure that no other peers with same ID are connected to the server
        if handshake.id in Peer.routing_table or handshake.id == Peer.id():
            Peer.logger.error(
                f"[ServerWorker] Peer with ID {handshake.id} already connected. Handhake failed"
            )
            # Notify the client + share our id
            ack = HandshakeResponse(error=True)
            send(
                conn,
                PeerMessage(
                    type=PeerMessageType.HANDSHAKE_RESPONSE, handshakeResponse=ack
                ),
            )
            return handshake.id, False

        # Send back success ack
        ack = HandshakeResponse(id=Peer.id(), error=False)
        send(
            conn,
            PeerMessage(type=PeerMessageType.HANDSHAKE_RESPONSE, handshakeResponse=ack),
        )
        return (handshake.id, True)

    @staticmethod
    def _send_handshake(conn: socket.socket, attempts=3) -> tuple[int, bool]:
        # Send the handshake start message
        Peer.logger.debug("[Handshake] Sending handshake start message")
        handshake = HandshakeStart(id=Peer.id())
        send(
            conn,
            PeerMessage(type=PeerMessageType.HANDSHAKE_START, handshakeStart=handshake),
        )

        # Receive back the response
        try:
            Peer.logger.debug("[Handshake] Waiting for handshake response...")
            res = receive(conn)
        except ConnectionResetError:
            raise ConnectionError(
                "Connection reset by peer during handshake. ID in use."
            )

        # Ensure that the response is an ack message
        if res.type != PeerMessageType.HANDSHAKE_RESPONSE:
            raise ConnectionError("Unexpected message type received during handshake")
        # Check if the handshake was successful
        res = res.handshakeResponse
        # Check if the handshake was successful
        if not res.error:
            Peer.logger.debug(f"[Handshake] Handshake successful. Peer ID: {res.id}")
            return res.id, True
        else:
            # Retry using the provided ID
            attempts -= 1
            if attempts > 0:
                # Generate a new peer ID
                Peer.set_random_id()
                # Retry again
                Peer.logger.warning(
                    f"[Handshake] Handshake failed. Retrying with new ID: {Peer.id()}"
                )
                return Peer._send_handshake(conn)
            Peer.logger.error("[Handshake] Too many attempts. Exiting...")
            return -1, False

    @staticmethod
    def receive_message(conn: socket.socket) -> Optional[PeerMessage]:
        try:
            return receive(conn)
        except ConnectionResetError:
            Peer.logger.error("Connection reset by peer")
            return None

    @staticmethod
    def handle_message(message: PeerMessage) -> None:
        # Handle incoming messages
        if message.type == PeerMessageType.MESSAGE:
            msg = message.message
            # If the target is not us, forward the message
            if msg.to != Peer.id():
                try:
                    # If we don't know how to reach the target, save it locally
                    if msg.to not in Peer.routing_table:
                        raise NoRouteError()
                    else:
                        Peer.logger.debug(
                            f"[OUTBOX] Forwarding message to {msg.to} via {Peer.routing_table[msg.to]}"
                        )
                        # Find route to the peer and forward the message
                        send(Peer.find_route(msg.to), message)
                except NoRouteError:
                    Peer.logger.error(
                        f"[Routing] No route to {msg.to}. Saving message for later..."
                    )
                    if msg.to not in Peer.buffer:
                        Peer.buffer[msg.to] = []
                    Peer.buffer[msg.to].append(message)
            else:
                Peer.logger.debug(f"[INBOX] Received new message from {msg.fr}")
                print(f"[Peer {msg.fr}]: {msg.msg}")
        # Handling broadcast messages (announcements)
        elif message.type == PeerMessageType.ANNOUNCEMENT:
            ann = message.announcement
            # Join announcement
            if ann.type == AnnouncementType.JOIN:
                Peer.routing_table.add_remote_peer(ann.join.id, ann.join.via_id)
            # Leave announcement
            elif message.announcement.type == AnnouncementType.LEAVE:
                del Peer.routing_table[ann.leave.id]
        else:
            Peer.logger.warning(
                f"[Client] Received unknown message type: {message.type}"
            )
            Peer.logger.debug(f"[Client] Message: {message}")

    @staticmethod
    def id() -> Optional[int]:
        return Peer._ID

    @staticmethod
    def set_id(uid: int) -> None:
        Peer._ID = uid

    @staticmethod
    def set_random_id() -> None:
        Peer._ID = derive_id(randint(0, 2**32))

    @staticmethod
    def join(ip: str, port: int) -> tuple[int, socket.socket]:
        # Connect to the peer using a socket
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            conn.connect((ip, port))
        except ConnectionRefusedError:
            raise ConnectionError("Connection refused by peer")

        # Perform handshake (only one attempt)
        peer_id, status = Peer._send_handshake(conn, attempts=1)

        if not status:
            raise ConnectionError("Handshake failed. Exiting...")
        assert peer_id > 0, "Invalid peer ID received. Check handshake logic."

        # Return the peer and its connection
        return (peer_id, conn)

    @staticmethod
    def find_route(uid: int) -> socket.socket:
        if uid in Peer.routing_table:
            # Send the message to the peer
            conn, via = Peer.routing_table[uid]
            if conn:
                return conn
            elif via:
                # Look for a route to the peer
                _max_hops = len(Peer.routing_table)
                while not conn and _max_hops > 0:
                    if not via:
                        break
                    _max_hops -= 1
                    conn, via = Peer.routing_table[via]
                # Check if a connection was found or if the max hops was reached
                if _max_hops == 0 or conn is None:
                    raise NoRouteError()
                return conn
            else:
                raise NoRouteError()
        else:
            raise NoRouteError()
