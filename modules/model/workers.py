import select
from abc import abstractmethod
from socket import socket
from threading import Thread
from typing import Callable

from gen.proto.communication_pb2 import (
    AnnouncementType,
    Join,
    Leave,
    PeerMessage,
    PeerMessageType,
    PropagationMessage,
)
from modules.lib.network import send
from modules.lib.peer import Peer
from modules.model.errors import ClosingConnectionError

type Address = tuple[str, int]


class ConnectionWorker(Thread):
    def __init__(self, conn: socket, addr: Address):
        super().__init__()
        self._conn = conn
        self._addr = addr
        if self._conn is None:
            raise ValueError("You have to pass a valid connection. Found None")

    @abstractmethod
    def run(self) -> None:
        pass

    def stop(self):
        self._conn.close()


# Server worker that listens for incoming connections and spawns specialized workers
class ServerAccessWorker(ConnectionWorker):
    def __init__(
        self,
        conn: socket,
        addr: Address,
        serve: Callable[[socket, Address], None],
    ):
        super().__init__(conn, addr)
        self.serve = serve

    def run(self) -> None:
        with self._conn:
            while not Peer.EXIT_EVENT.is_set():
                # Start listening for connections
                Peer.logger.info("[ServerListener] Listening for connections...")
                self._conn.listen()
                # Accept connections
                try:
                    conn, addr = self._conn.accept()
                except ConnectionAbortedError as e:
                    Peer.logger.error(
                        f"[ServerListener] Connection aborted: {e}. Quitting..."
                    )
                    Peer.EXIT_EVENT.set()
                    break

                Peer.logger.info(
                    "[ServerListener] Connection accepted. Creating worker..."
                )

                # Server client
                self.serve(conn, addr)


class PeerWorker(ConnectionWorker):
    def __init__(self, conn: socket, addr: Address):
        super().__init__(conn, addr)

    @abstractmethod
    def prepare(self):
        pass

    @abstractmethod
    def closing(self):
        pass

    def listen(self):
        # Start listening
        while not Peer.EXIT_EVENT.is_set():
            # Check for incoming messages every second
            try:
                ready_sockets, _, _ = select.select(
                    [self._conn], [], [], 1
                )  # 1 second timeout
                if ready_sockets:
                    msg = Peer.receive_message(self._conn)
                    if msg is None:
                        Peer.logger.info("[PeerServerWorker] Connection closed")
                        break
                    # Handle message
                    Peer.handle_message(msg)
            except OSError as e:
                Peer.logger.error(f"[PeerServerWorker] Error: {e}")
                raise ClosingConnectionError(
                    f"An error occurred while listening for messages: {e}"
                )
        # Notify that we are closing the connection
        raise ClosingConnectionError("Closing connection")

    def run(self) -> None:
        try:
            self.prepare()
            self.listen()
        except ClosingConnectionError as e:
            Peer.logger.info(f"[PeerWorker] Closing connection: {e}")
        finally:
            Peer.logger.info("[PeerWorker] Stopping worker...")
            self.closing()
            self.stop()


# Worker that handles the connection with a peer
class PeerServerWorker(PeerWorker):
    def __init__(self, conn: socket, addr: Address):
        super().__init__(conn, addr)
        self._peer_id: int | None = None

    def prepare(self):
        # Handle connection with peer!
        Peer.logger.debug("[PeerServerWorker] Starting worker...")

        # Handle handshake with peer
        uid, status = Peer.handle_handshake(self._conn)
        if not status:
            Peer.logger.warning(
                "[PeerServerWorker] Handshake failed. Closing connection."
            )
            return
        self._peer_id = uid  # store peer id in global variable to be used later

        # If the handshake was successful, add the peer to the routing table
        Peer.logger.info(f"[PeerServerWorker] Peer {uid} connected successfully")
        Peer.routing_table.add_local_peer(uid, self._conn)

        # If there are some buffered messages, sent them all
        if uid in Peer.buffer:
            if len(Peer.buffer[uid]) > 0:
                for msg in Peer.buffer[uid]:
                    send(self._conn, msg)
                Peer.buffer[uid].clear()

        # Share the routing table with the new peer
        if len(Peer.routing_table) > 1:
            Peer.logger.debug(f"[PeerServerWorker] Sharing routing table with {uid}...")
            for peer_id, _ in Peer.routing_table:
                if peer_id != uid:
                    join_ann = PeerMessage(
                        type=PeerMessageType.ANNOUNCEMENT,
                        announcement=PropagationMessage(
                            type=AnnouncementType.JOIN,
                            join=Join(id=peer_id, via_id=Peer.id()),
                        ),
                    )
                    send(self._conn, join_ann)
        else:
            Peer.logger.debug(
                f"[PeerServerWorker] Routing table is empty. Nothing to share with {uid}"
            )

        # Notify all peers that a new peer has joined
        join_ann = PeerMessage(
            type=PeerMessageType.ANNOUNCEMENT,
            announcement=PropagationMessage(
                type=AnnouncementType.JOIN, join=Join(id=uid, via_id=Peer.id())
            ),
        )

        if len(Peer.routing_table) > 1:
            Peer.logger.debug(
                f"[PeerServerWorker] Notifying all peers that {uid} has joined"
            )
            for peer_id, (conn, _) in Peer.routing_table:
                if not conn or peer_id == uid:
                    continue
                Peer.logger.info(
                    f"[PeerServerWorker] Notifying peer {peer_id} that {uid} has joined"
                )
                send(conn, join_ann)
        else:
            Peer.logger.debug(
                "[PeerServerWorker] Routing table is empty. Nothing to notify other peers"
            )

    def closing(self):
        # Closing connection with peer, if any was established
        if not self._peer_id:
            return
        # Remove peer from routing table
        del Peer.routing_table[self._peer_id]
        # Send leave message to all peers
        leave_ann = PeerMessage(
            type=PeerMessageType.ANNOUNCEMENT,
            announcement=PropagationMessage(
                type=AnnouncementType.LEAVE, leave=Leave(id=self._peer_id)
            ),
        )
        # Send leave message to all peers
        for _, (conn, _) in Peer.routing_table:
            if not conn:
                continue
            send(conn, leave_ann)


# Worker that only receives messages from an already connected peer
class PeerClientWorker(PeerWorker):
    def __init__(self, peer_id: int, conn: socket, addr: Address):
        super().__init__(conn, addr)
        self._peer_id = peer_id

    # NOTE: Nothing to prepare. Go straight to listening
    def prepare(self):
        pass

    def closing(self):
        # Remove peer from routing table when server closes
        del Peer.routing_table[self._peer_id]
