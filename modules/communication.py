from random import randint


class RoutingTable:
    def __init__(self):
        self.routing_table = {}

    def add_entry(self, id: int, addr: tuple[str, str], conn: object):
        self.routing_table[id] = (addr, conn)

    def get_entry(self, id: int):
        return self.routing_table.get(id, None)


def send_message(conn, m):
    serialized = m.SerializeToString()
    conn.sendall(len(serialized).to_bytes(4, byteorder="big"))
    conn.sendall(serialized)


def receive_message(conn, m):
    msg = m()
    size_data = conn.recv(4)
    if not size_data:
        raise ConnectionResetError("Connection closed by peer during size reception")

    size = int.from_bytes(size_data, byteorder="big")
    data = conn.recv(size)
    if len(data) < size:
        raise ConnectionResetError("Incomplete message received")

    msg.ParseFromString(data)
    return msg
