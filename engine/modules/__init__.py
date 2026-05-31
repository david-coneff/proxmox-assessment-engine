# Import all parser modules so their @register_parser decorators fire on import.
from engine.modules import (  # noqa: F401
    hardware_parser,
    storage_parser,
    network_parser,
    proxmox_parser,
    guest_parser,
)
