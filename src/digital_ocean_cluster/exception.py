class DropletException(Exception):
    def __init__(self, message: str, droplet: str) -> None:
        self.message = message
        self.droplet = droplet
        super().__init__(message)

    def __str__(self) -> str:
        return f"DropletException(droplet={self.droplet}, message={self.message})"
