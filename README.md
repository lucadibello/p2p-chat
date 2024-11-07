# Peer-to-Peer Network Server Project

This project provides a peer-to-peer (P2P) network server where each peer functions as both a client and a server, facilitating decentralized communication across multiple nodes. Each peer is uniquely identified, allowing it to either join an existing network or create a new one if none is specified. The server manages peer connections, message exchange, connection lifecycle management, and duplicate connection prevention, making it suitable for decentralized applications.

## Table of Contents

1. [Features](#features)
2. [Architecture Overview](#architecture-overview)
3. [Getting Started](#getting-started)
4. [Usage](#usage)
5. [Protocol Buffers (Protobuf) Specification](#protocol-buffers-protobuf-specification)
6. [Key Classes](#key-classes)
7. [Example Scenario](#example-scenario)
8. [Future Improvements](#future-improvements)

## Features

- **Dual Role for Peers**: Each peer operates as both a client and a server, meaning it can connect to an existing network or host a new one.
- **Peer-to-Peer Messaging**: Supports direct peer-to-peer messaging, with message types like basic messages, announcements, and handshake exchanges.
- **Threaded Connection Management**: Each peer connection has its own threaded handler for handling incoming and outgoing messages.
- **Network Creation and Joining**: Peers can create a new network if they don’t specify an existing peer to connect to.
- **Duplicate Connection Prevention**: Uses a unique ID for each peer and prevents multiple connections with the same ID.
- **Graceful Shutdown and Error Handling**: Automatically handles disconnections and errors, with logging and notifications to other peers.
- **Dynamic Peer Announcements**: Propagates announcements (like join and leave events) to update peers on network changes.

## Architecture Overview

The project is built on a multi-threaded server architecture. Each peer is a self-contained client and server. Key components include:

- **ConnectionWorker**: Base class for managing peer connections, implementing thread-based handling.
- **ServerAccessWorker**: Listens for incoming connections and spawns new connection workers.
- **PeerWorker**: Extends `ConnectionWorker` for peer management; handles message listening and error management.
- **PeerServerWorker**: Specialized worker that manages handshake validation, announcements, and updates the routing table.
- **PeerServer**: The main server class that manages connection threads, tracks active peers, and propagates network changes.

### Network Behavior

If a peer does not specify a peer to connect to during startup, it will initiate a new network, acting as the first node and waiting for others to connect. If a peer specifies an existing network’s IP and port, it attempts to join that network, conducting a handshake to establish its presence and exchanging identification data.

## Getting Started

### Prerequisites

- **Python 3.x**
- **Protobuf Compiler**: Required for compiling `.proto` files if they need to be modified.
- **Network Access**: Ensure appropriate firewall and network permissions for the chosen IP and port.

### Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/lucadibello/p2p-chat.git
   cd peer-to-peer-server
   ```

2. **Create and activate Conda environment**:

   ```bash
   conda create --name p2p python=3.9
   cond activate p2p
   ```

3. **Compile Protobuf Definitions**:

   ```bash
   make generate
   ```

## Usage

### Command-Line Usage

Each peer instance is started using `peer.py` with the following command-line options:

```plaintext
usage: peer.py [-h] [--desired-id DESIRED_ID] [--log-level LOG_LEVEL] local_address [peer_address]

Peer to peer

positional arguments:
  local_address         Your IP and port in the format [my_ip]:[my_port]
  peer_address          Optional peer address in the format [peer_ip]:[peer_port]

options:
  -h, --help            show this help message and exit
  --desired-id DESIRED_ID
                        An optional unique ID
  --log-level LOG_LEVEL
                        The log level to use. Valid values are DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Example Usage

1. **Starting a New Network**: To create a new network, specify only the `local_address` without `peer_address`. This peer will act as the initial server for others to connect to.

   ```bash
   python peer.py 192.168.1.10:5000 --desired-id 10
   ```

2. **Joining an Existing Network**: To join an existing network, specify both `local_address` and `peer_address`.

   ```bash
   python peer.py 192.168.1.11:5001 192.168.1.10:5000 --desired-id 11
   ```

3. **Optional Parameters**:
   - **--desired-id**: Specify a unique ID for the peer. If not provided, a random ID will be generated.
   - **--log-level**: Set the log level for output, such as `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`.

## Protocol Buffers (Protobuf) Specification

The project defines structured messages using Protocol Buffers (Protobuf) to standardize communication between peers. Here’s a breakdown of the message types:

- **PeerMessageType**: Enum defining message types (MESSAGE, ANNOUNCEMENT, HANDSHAKE).
- **AnnouncementType**: Enum defining announcement types (JOIN, LEAVE).
- **PeerMessage**: Root message with a oneof structure, allowing different message types.
- **Message**: Basic peer-to-peer message with sender, receiver, and message content.
- **HandshakeStart** and **HandshakeResponse**: Messages for the handshake protocol between peers and the server.
- **PropagationMessage**: Used for announcements such as JOIN and LEAVE, notifying all peers of network changes.

## Key Classes

- **`ConnectionWorker`**: Base class for handling individual connections with abstract methods for running and stopping threads.
- **`ServerAccessWorker`**: Server worker that listens for new connections and starts `PeerServerWorker` instances for each.
- **`PeerWorker`**: Extends `ConnectionWorker` for peer management; handles message listening and error management.
- **`PeerServerWorker`**: Specialized worker that manages handshake validation, announcements, and updates the routing table.
- **`PeerServer`**: The main server class that manages connection threads, tracks active peers, and propagates network changes.

## Example Scenario

### Scenario: Chat Application

1. **Starting the Server**:

   - The server starts listening on a specified IP and port.

2. **Peer A Connects**:

   - Peer A connects with a unique ID ("UserA") and successfully completes the handshake.
   - The server adds Peer A to the routing table and announces the connection to other peers (if any).

3. **Peer B Attempts to Connect with the Same ID**:

   - Peer B attempts to connect with ID "UserA", but the server detects a duplicate and rejects the connection.

4. **Peer B Connects with a New ID**:

   - Peer B reconnects with a unique ID ("UserB") and is accepted.
   - The server updates the routing table and announces Peer B’s presence to Peer A.

5. **Messaging**:

   - Peer A sends a message directly to Peer B.
   - Peer B receives the message and can respond, establishing direct peer-to-peer communication.

6. **Disconnection**:
   - Peer A disconnects from the server.
   - The server updates the routing table, removes Peer A, and broadcasts a leave announcement to Peer B.
