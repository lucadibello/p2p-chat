from threading import Thread
from modules import protocol
from modules.config import ServerAddress
from modules.errors import ValidationError
from modules.logger import Logger
from modules.buffer import PeerBuffer
import modules.communication as comm
from gen.proto.communication_pb2 import HandshakeStart, HandshakeAck, Message
from modules.args import parse_args
import socket
import sys
import logging

# Initialize logger
log_dir = "./log"
logger = Logger("peer", logging.DEBUG).get_logger()

# General behavior variables
EXIT = False
PEER_ID = None

# Initialize routing table
TABLE = {}

# Initialize per-peer buffer of messages
buffer = PeerBuffer()


def peer_server_thread(conn: socket.socket, addr: tuple):
    with conn:
        # Wait for the client to send the HandshakeStart message
        handshake = comm.receive_message(conn, HandshakeStart)

        # Ensure that there are no clients with the same name in the routing table
        if handshake.id in TABLE:
            newid = protocol.generate_peer_id()
            while newid in TABLE:
                newid = protocol.generate_peer_id()
            comm.send_message(conn, HandshakeAck(id=newid, error=True))
            logger.debug(
                f"Handshake with client {handshake.id} failed. Retrying with new ID {newid}."
            )
        else:
            comm.send_message(conn, HandshakeAck(id=handshake.id, error=False))
            logger.debug(f"Handshake with client {handshake.id} completed.")

        # Save client connection and address
        TABLE[handshake.id] = (conn, addr)
        # Propagate the update to the whole network
        # TODO: Send propagation message to whole routing table entries

        # Wait for incoming messages
        while True:
            try:
                message = comm.receive_message(conn, Message)
            except ValueError:
                logger.error(f"Error receiving message from {handshake.id}")
                break
            # Check if the message is an exit message
            if message.msg == "end":
                logger.info(f"Client {handshake.id} requested to close the connection.")
                del TABLE[handshake.id]
                # Propagate the update to the whole network
                # FIXME: Send propagation message to whole routing table entries
                break
            # Check if the message is intended for the server
            if message.to == PEER_ID:
                logger.info(f"Message from {message.fr}: {message.msg}")
            else:
                # Forward the message to the recipient
                if message.to in TABLE:
                    recipient_conn, _ = TABLE[message.to]
                    comm.send_message(recipient_conn, message)
                    logger.info(f"Forwarded message from {message.fr} to {message.to}")
                else:
                    logger.error(
                        f"Recipient {message.to} not found in the routing table."
                    )
                    # Save the message in the buffer
                    buffer.add_message(message.fr, message)
                    # Propagate the update to the whole network
                    # FIXME: implement this


def peer_server(server_config: ServerAddress):
    logger.info(f"Starting server on {server_config['ip']}:{server_config['port']}")

    # Wait for incoming connections
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((server_config["ip"], server_config["port"]))
        logger.info(f"[Server] P2P server started on port {server_config["port"]}")
        s.listen()

        # Accept incoming connections
        while True:
            try:
                conn, addr = s.accept()
                logger.info(f"[Server] Accepted connection from {addr}")

                # Start the client thread
                client = Thread(target=peer_server_thread, args=(conn, addr))
                client.start()
            except KeyboardInterrupt:
                break
    logger.info("[Server] P2P server closed.")


def main(raw_args: list):
    global PEER_ID

    logger.info("Parsing arguments...")
    # parse and validate arguments
    try:
        config = parse_args(raw_args)
    except ValidationError as e:
        logger.error(f"Error message: {e.message}")
        logger.error("Fields:")
        for source, msg in e.fields:
            logger.error(f"  - {source}: {msg}")
        return

    # Generate or use provided peer ID
    PEER_ID = config["id"] if config["id"] is not None else protocol.generate_peer_id()

    # Start the server as a thread
    logger.debug("Creating peer server thread...")
    tserver = Thread(target=peer_server, args=(config["local"],))
    tserver.daemon = True  # Close the server when the main thread finishes
    tserver.start()

    # Try to connect to the peer
    logger.debug("Connecting to the peer...")
    peer_address = config["peer"]
    if peer_address is None:
        logger.warning("No peer address provided. **Running as server only**.")
        tserver.join()  # Wait until the server thread finishes
    else:
        # Otherwise, connect to peer
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((peer_address["ip"], peer_address["port"]))

                # Try to perform the handshake with the desired ID (or generate if not provided)
                status, id = protocol.perform_handshake(s, PEER_ID)

                # if the handshake failed, retry the connection using the provided id
                if not status:
                    status, id = protocol.perform_handshake(s, id)
                    if not status:
                        logger.error("[Client] Handshake failed. Closing connection.")
                        return

                logger.info(f"[Client] Handshake completed. Final ID: {id}")

                # Send messages to the server
                while True:
                    # Ask the user
                    try:
                        data = input("Enter a message: ")
                    except ValueError:
                        data = "end"

                    if EXIT:
                        print("Connection closed by the server... Exiting")
                        break
                    elif data == "end":
                        break
                    elif data == "":
                        continue  # Reprint the prompt if the user didn't enter anything

                    # Ensure that the user has specified a recipient id
                    parts = data.split(" ")
                    content = " ".join(parts[1:])
                    try:
                        recipient_id = int(parts[0])
                    except ValueError:
                        print(
                            "Invalid message. Please specify a recipient id before the message"
                        )
                        continue  # Skip the rest of the loop

                    # Send text to user
                    protocol.send_text(s, id, recipient_id, content)
                    logger.info(f"[Client] Sent message to {recipient_id}")

        except ValueError as e:
            logger.error(f"Error: {e}")
            return


if __name__ == "__main__":
    main(sys.argv[1:])
