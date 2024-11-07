from gen.proto.communication_pb2 import (
    Message,
    PeerMessage,
    PeerMessageType,
)


# Lambda to create a new text message
def make_message(fr: int, to: int, text: str) -> PeerMessage:
    return PeerMessage(
        type=PeerMessageType.MESSAGE, message=Message(fr=fr, to=to, msg=text)
    )
