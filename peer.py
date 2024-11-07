from sys import argv

import modules.lib.args as args
from gen.proto.communication_pb2 import (
    PeerMessage,
)
from modules.lib.input import read_command
from modules.lib.network import send
from modules.lib.peer import Peer
from modules.lib.server import PeerServer
from modules.model.config import Config
from modules.model.errors import InvalidMessageError, NoRouteError, ValidationError
from modules.model.factory import make_message as _make_message
from modules.model.workers import PeerClientWorker, PeerServerWorker

# Set global states
MAX_PEERS = 10

# Initialize some objects
config: Config | None = None


def validate_args(raw_args: list[str]) -> Config:
    Peer.logger.info("[Startup] Peer to peer network. Starting...")

    # parse and validate arguments
    Peer.logger.debug("[Startup] Parsing and validating arguments...")
    try:
        config = args.parse(raw_args)
    except ValidationError as e:
        Peer.logger.error(f"[Startup] Error message: {e.message}")
        Peer.logger.error("Fields:")
        for source, msg in e.fields:
            Peer.logger.error(f"  - {source}: {msg}")
        exit(1)
    Peer.logger.debug("[Startup] Arguments parsed and validated successfully")
    return config


def main(raw_args: list[str]) -> None:
    global config, routing_table, buffer

    # Validate the program arguments
    config = validate_args(raw_args)

    # Apply the desired log level
    Peer.logger.setLevel(config["log_level"])

    # If user has set a desired ID, set it. Otherwise, use a random ID
    if config["id"] is not None:
        Peer.set_id(config["id"])
    else:
        Peer.set_random_id()

    # Override the make_message function to inclide the ID
    def make_message(uid: int, msg: str) -> PeerMessage:
        peerid = Peer.id()
        assert peerid is not None, "Peer ID is not set"
        return _make_message(peerid, uid, msg)

    # check whether we want to create a new network or
    # access an existing one using an handshake request
    if config["peer"] is not None:
        # Try to connect to the peer
        try:
            Peer.logger.info("[Startup] Connecting to the peer...")
            addr = (config["peer"]["ip"], config["peer"]["port"])
            uid, conn = Peer.join(addr[0], addr[1])

            # Record the connection inside the routing table
            Peer.logger.info("[Startup] Connection successful.")
            Peer.routing_table.add_local_peer(uid, conn)

            # Start a worker thread to handle all incoming messages
            worker = PeerClientWorker(uid, conn, addr)
            worker.start()
        except ConnectionError as e:
            Peer.logger.error(f"[Startup] Handshake failed: {e}")
            exit(1)

    else:
        Peer.logger.info("[Startup] Creating a new network...")

    # Start the server thread
    server = PeerServer(
        config["local"]["ip"], config["local"]["port"], PeerServerWorker, MAX_PEERS
    )
    try:
        server.start()
    except OSError as e:
        Peer.logger.error(f"[Startup] Error starting server: {e}")
        exit(1)

    # Start the client
    while not Peer.EXIT_EVENT.is_set():
        try:
            uid, msg = read_command()
        except InvalidMessageError as e:
            Peer.logger.error(f"Invalid message: {e}")
            continue

        if uid is None:
            # Handling special events
            if msg == "":
                continue
            elif msg == "table":
                Peer.logger.info("[Routing Table]")
                Peer.routing_table.print_routing_table()
            elif msg == "exit":
                Peer.EXIT_EVENT.set()
                break
            elif msg == "buffer":
                Peer.logger.info("[Buffer]")
                if len(Peer.buffer) == 0:
                    Peer.logger.warning("  - No messages in the buffer")
                else:
                    for uid, msgs in Peer.buffer.items():
                        Peer.logger.info(f"   [{uid}]: {len(msgs)} messages")
            else:
                Peer.logger.error("Invalid command. Please try again.")
                continue
        elif uid == Peer.id():
            Peer.logger.error("You cannot send a message to yourself!")
            continue
        else:
            Peer.logger.debug(f"[Console] Sending message to {uid} with content: {msg}")
            try:
                # If the UID is known, try to look for a route to it
                if uid in Peer.routing_table:
                    send(Peer.find_route(uid), make_message(uid, msg))
                else:
                    raise NoRouteError()
            except NoRouteError:
                Peer.logger.error(
                    f"[Routing] No route to {uid}. Saving message for later..."
                )
                if uid not in Peer.buffer:
                    Peer.buffer[uid] = []
                Peer.buffer[uid].append(make_message(uid, msg))
                continue

    # Stop the server
    Peer.logger.info("[Shutdown] Exiting the program...")
    # Force the server to stop and close all connections
    server.stop()


if __name__ == "__main__":
    try:
        main(argv[1:])
    except KeyboardInterrupt:
        Peer.logger.info("[Shutdown] Keyboard interrupt detected. Shutting down...")
    except ConnectionError as e:
        Peer.logger.error("[Shutdown] Connection error detected...")
        Peer.logger.exception(e)
    except Exception as e:
        Peer.logger.error("[Shutdown] An error occurred:")
        Peer.logger.exception(e)
