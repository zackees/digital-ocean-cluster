from threading import Lock

_PRINT_LOCK = Lock()


def locked_print(*args, **kwargs):
    # open log file
    with _PRINT_LOCK:
        try:
            print(*args, **kwargs)

        except UnicodeDecodeError as ue:
            print(f"Error in locked_print: {ue}")
