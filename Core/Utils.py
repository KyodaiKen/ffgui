import os

def format_duration(seconds):
    """
    Converts seconds into a string format: 0d 0h 0m 0.000s
    """
    if seconds is None:
        return "0d 0h 0m 0.000s"
    
    d = int(seconds // 86400)
    h = int((seconds % 86400) // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{d}d {h}h {m}m {s:.3f}s"

def get_file_title(filename):
    """
    Gets the title of the filename provided.
    Example: /my/path/to/the/file.dat
    Returns: file.dat
    """
    return os.path.basename(filename)