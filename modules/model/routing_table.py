from typing import Dict, Optional
import socket


class RoutingTable:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(RoutingTable, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "routing_table"):
            self.routing_table: Dict[
                int, tuple[Optional[socket.socket], Optional[int]]
            ] = {}

    def add_local_peer(self, id: int, conn: socket.socket, via_id=None):
        self.routing_table[id] = (conn, via_id)

    def add_remote_peer(self, id: int, via_id: int):
        self.routing_table[id] = (None, via_id)

    def get_routing_table(self):
        return self.routing_table

    def __contains__(self, id: int):
        return id in self.routing_table

    def __str__(self):
        return str(self.routing_table)

    def __repr__(self):
        return str(self.routing_table)

    def __iter__(self):
        return iter(self.routing_table.items())

    def __len__(self):
        return len(self.routing_table)

    def __delitem__(self, id: int):
        del self.routing_table[id]

    def __getitem__(self, id: int):
        return self.routing_table[id]

    def print_routing_table(self):
        print()
        print("Routing Table:")
        print("ID | Peer | Via")
        for id, (peer, via) in self.routing_table.items():
            print(f"{id} | {peer} | {via}")
        print()
