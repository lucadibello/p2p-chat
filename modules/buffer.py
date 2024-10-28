from gen.proto.communication_pb2 import Message


class PeerBuffer:
    def __init__(self):
        self.buffer: dict[int, list[tuple[int, Message]]] = {}

    def add_message(self, sender: int, message: Message):
        if message.to not in self.buffer:
            self.buffer[message.to] = []
        self.buffer[message.to].append((sender, message))

    def get_messages(self, peer_id: int) -> list[tuple[int, Message]]:
        if peer_id in self.buffer:
            return self.buffer[peer_id]
        return []

    def has_messages(self, peer_id: str):
        return peer_id in self.buffer
