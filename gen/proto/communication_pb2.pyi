from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class Message(_message.Message):
    __slots__ = ("fr", "to", "msg")
    FR_FIELD_NUMBER: _ClassVar[int]
    TO_FIELD_NUMBER: _ClassVar[int]
    MSG_FIELD_NUMBER: _ClassVar[int]
    fr: int
    to: int
    msg: str
    def __init__(self, fr: _Optional[int] = ..., to: _Optional[int] = ..., msg: _Optional[str] = ...) -> None: ...

class HandshakeStart(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: int
    def __init__(self, id: _Optional[int] = ...) -> None: ...

class HandshakeAck(_message.Message):
    __slots__ = ("id", "error")
    ID_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    id: int
    error: bool
    def __init__(self, id: _Optional[int] = ..., error: bool = ...) -> None: ...
