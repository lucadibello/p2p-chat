import socket
from abc import ABC, abstractmethod
from threading import Thread
from typing import Generic, Type, TypeVar

from modules.lib.peer import Peer
from modules.model.workers import Address, PeerServerWorker, ServerAccessWorker


class Server(ABC):
    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port
        self._connected = False
        self._socket: socket.socket | None = None

    @abstractmethod
    def serve(self, conn: socket.socket, addr: Address):
        pass

    def stop(self):
        # Close socket
        if not self._connected:
            raise ConnectionError("Server is not connected")

        # If connected, socket is not None
        assert self._socket is not None
        self._socket.close()

    def _connect(self):
        if self._connected:
            raise ConnectionError("Server is already connected")

        # Open socket connection
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind((self._host, self._port))

        # Set connected flag
        self._connected = True

    @abstractmethod
    def start(self) -> None:
        pass


class ThreadedServer(Server):
    def __init__(self, host: str, port: int, max_connections: int = 10):
        super().__init__(host, port)
        self._max_connections = max_connections
        self._workers = []
        self._index = 0
        self._listener: Thread | None = None

    @abstractmethod
    def create_worker(self, conn: socket.socket, addr: Address) -> Thread:
        pass

    def serve(self, conn: socket.socket, addr: Address):
        # Check if connection limit is reached
        if len(self._workers) >= self._max_connections:
            conn.close()
            Peer.logger.warning(
                "Connection limit reached. Cannot serve more connections."
            )
            return

        # cast to tuple[str, int]
        try:
            addr = (addr[0], int(addr[1]))  # type: ignore
        except ValueError:
            raise ValueError(f"Invalid address: {addr}")

        # Assert that the format is correct
        assert isinstance(addr[0], str) and isinstance(addr[1], int)

        # Otherwise, create a new worker to handle the connection
        self._index += 1
        worker = self.create_worker(conn, addr)  # type: ignore
        self._workers.append(worker)

        # Start worker thread
        worker.start()

    def start(self):
        # Ensure that this node is already part of a network (joined / created a new one)
        if Peer.id() is None:
            raise ConnectionError(
                "Peer ID is not set. Peer is not part of a network yet. Cannot start the server"
            )

        # Connect to the server
        super()._connect()

        Peer.logger.info(f"[Server] Starting listener at {self._host}:{self._port}...")

        # Ensure binding is successful
        assert self._socket is not None
        assert self._connected

        # Start connection listener
        self._listener = ServerAccessWorker(
            self._socket, (self._host, self._port), self.serve
        )
        self._listener.start()

    def stop(self):
        if not self._connected:
            raise ConnectionError("Server is not connected")

        # Stop all workers
        for worker in self._workers:
            worker.stop()
        # Ensure that all workers are stopped
        for worker in self._workers:
            worker.join()
        # Stop the server
        super().stop()

    def join(self):
        if self._listener is None:
            raise ConnectionError("Listener is not running")

        # Wait for the listener to finish
        self._listener.join()


T = TypeVar("T", bound=PeerServerWorker)


# Server specific for peer-to-peer communication
class PeerServer(ThreadedServer, Generic[T]):
    def __init__(
        self, host: str, port: int, worker_cls: Type[T], max_connections: int = 10
    ):
        super().__init__(host, port, max_connections)
        self.worker_cls = worker_cls  # Store the worker class

    def start(self):
        super().start()

    # Create a new worker to handle the connection
    def create_worker(self, conn: socket.socket, addr: tuple[str, int]) -> Thread:
        return self.worker_cls(conn, addr)
