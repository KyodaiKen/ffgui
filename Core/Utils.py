import os

@staticmethod
def get_file_title(filename):
    """
    Gets the title of the filename provided.
    Example: /my/path/to/the/file.dat
    Returns: file.dat
    """
    return os.path.basename(filename)

@staticmethod
def time_to_seconds(time_str):
    """Convert HH:MM:SS.FFF to total seconds."""
    try:
        if not time_str or ":" not in time_str:
            return 0.0
        parts = time_str.split(':')
        h = float(parts[0])
        m = float(parts[1])
        s = float(parts[2])
        return h * 3600 + m * 60 + s
    except (ValueError, IndexError):
        return 0.0

@staticmethod
def seconds_to_time(seconds):
    """Convert total seconds to HH:MM:SS.FFF."""
    if seconds < 0: seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02}:{m:02}:{s:06.3f}"