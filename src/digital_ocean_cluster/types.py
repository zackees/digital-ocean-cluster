from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from inspect import currentframe
from types import FrameType

THREAD_POOL = ThreadPoolExecutor(max_workers=64)


@dataclass
class Authentication:
    droplet_limit: int
    floating_ip_limit: int
    reserved_ip_limit: int
    volume_limit: int
    email: str
    name: str
    uuid: str
    email_verified: bool
    status: str
    team: dict[str, str]


@dataclass
class SSHKey:
    id: int
    name: str
    fingerprint: str
    public_key: str

    def __str__(self) -> str:
        return f"SSHKey: name={self.name},id={self.id},fingerprint={self.fingerprint}"


def _inspect_frame(frame: FrameType | None) -> tuple[str, int]:
    if frame:
        # Get the caller's frame (1 level up)
        caller_frame = frame.f_back
        if caller_frame:
            line = caller_frame.f_lineno
            file = caller_frame.f_code.co_filename
        else:
            line = 0
            file = "<unknown>"
        # frame.clear()  # Clear the frame reference to prevent reference cycles
    else:
        line = 0
        file = "<unknown>"
    return file, line


class DropletException(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        # Get the caller's frame to find the line number and file
        frame = currentframe()
        self.file, self.line = _inspect_frame(frame)
        super().__init__(message)

    def __str__(self) -> str:
        return f"{self.message} in {self.file} at line {self.line}"
