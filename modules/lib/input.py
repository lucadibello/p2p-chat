from typing import Optional
from modules.model.errors import (
    InvalidMessageError,
)


def read_command() -> tuple[Optional[int], str]:
    # Ask the user
    try:
        data = input("Enter a message: ")
    except ValueError:
        raise InvalidMessageError("You must enter a valid message.")

    # Preprocess input
    data = data.strip().lower()

    if data == "end":
        return (None, "exit")
    elif data == "":
        return (None, "")
    elif data == "table":
        return (None, "table")  # type: ignore
    elif data == "buffer":
        return (None, "buffer")

    # Process data as a "SEND" command
    parts = data.split(" ", 1)  # Split on the first space only
    if len(parts) < 2:
        raise InvalidMessageError("The format should be 'ID message'.")

    try:
        recipient_id = int(parts[0])  # Parse recipient ID
    except ValueError:
        raise InvalidMessageError("Invalid recipient ID. Should be a number.")

    content = parts[1]  # The message content
    return (recipient_id, content)
