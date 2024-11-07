import argparse
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL
import re
from modules.model.config import Config
from modules.model.errors import ValidationError


def parse(args) -> Config:
    parser = argparse.ArgumentParser(description="Peer to peer")
    parser.add_argument(
        "local_address", help="Your IP and port in the format [my_ip]:[my_port]"
    )
    parser.add_argument("--desired-id", type=int, help="An optional unique ID")
    parser.add_argument(
        "peer_address",
        nargs="?",
        help="Optional peer address in the format [peer_ip]:[peer_port]",
    )
    # add log level argument
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="The log level to use. Valid values are DEBUG, INFO, WARNING, ERROR, CRITICAL",
    )
    parsed_args = parser.parse_args(args)

    # Build the Config object with the information included in this data
    status, errors = _validate_args(parsed_args)
    if not status:
        raise ValidationError("Invalid arguments", errors)

    # Convert the log level to a valid integer value
    log_level = getattr(parsed_args, "log_level", "INFO")
    numeric_value = INFO
    if log_level == "DEBUG":
        numeric_value = DEBUG
    elif log_level == "INFO":
        numeric_value = INFO
    elif log_level == "WARNING":
        numeric_value = WARNING
    elif log_level == "ERROR":
        numeric_value = ERROR
    elif log_level == "CRITICAL":
        numeric_value = CRITICAL

    config = Config(
        id=parsed_args.desired_id,
        local={
            "ip": parsed_args.local_address.split(":")[0],
            "port": int(parsed_args.local_address.split(":")[1]),
        },
        peer={
            "ip": parsed_args.peer_address.split(":")[0],
            "port": int(parsed_args.peer_address.split(":")[1]),
        }
        if parsed_args.peer_address
        else None,
        log_level=numeric_value,
    )

    return config


type ErrorList = list[tuple[str, str]]


def _validate_args(parsed_args) -> tuple[bool, ErrorList]:
    def validate_ip_port(address):
        ip_port_pattern = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}:\d{1,5}$")
        if not ip_port_pattern.match(address):
            raise ValueError(
                f"Invalid address format: '{address}'. Expected format is [ip]:[port]."
            )

        ip, port = address.split(":")
        # Validate IP address ranges
        ip_parts = list(map(int, ip.split(".")))
        if not all(0 <= part < 256 for part in ip_parts):
            raise ValueError(
                f"Invalid IP address: '{ip}'. Each octet should be between 0 and 255."
            )

        # Validate port range
        if not (0 < int(port) <= 65535):
            raise ValueError(
                f"Invalid port number: '{port}'. Port should be in the range 1-65535."
            )

    # Validate the log level
    def validate_log_level(log_level):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level not in valid_levels:
            raise ValueError(
                f"Invalid log level: '{log_level}'. Valid values are: {', '.join(valid_levels)}"
            )

    status = True
    errors = list[tuple[str, str]]()

    # Validate my_address
    try:
        validate_ip_port(parsed_args.local_address)
    except ValueError as e:
        errors.append(("local_address", str(e)))
        status = False

    # Validate peer_address if provided
    if parsed_args.peer_address:
        try:
            validate_ip_port(parsed_args.peer_address)
        except ValueError as e:
            errors.append(("peer_address", str(e)))
            status = False

    # Validate the log level
    if parsed_args.log_level:
        try:
            validate_log_level(parsed_args.log_level)
        except ValueError as e:
            errors.append(("desired_id", str(e)))
            status = False

    # Return status and the error message
    return status, errors
