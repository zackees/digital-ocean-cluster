from inspect import currentframe
from types import FrameType


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
        frame.clear()  # Clear the frame reference to prevent reference cycles
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
