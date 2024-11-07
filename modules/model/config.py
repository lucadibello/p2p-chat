from typing import TypedDict


class ServerAddress(TypedDict):
    ip: str
    port: int


class Config(TypedDict):
    id: int
    local: ServerAddress
    peer: ServerAddress | None
    log_level: int
