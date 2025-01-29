import platform

class Config:
    """Application configuration."""
    TIMEOUT = 2  # Time limit in seconds
    MEMORY_LIMIT_MB = 100  # Memory limit in MB
    IS_WINDOWS = platform.system() == "Windows"
    
    # Security-critical set of restricted modules
    RESTRICTED_MODULES = {
        # Filesystem
        "os", "sys", "shutil", "pathlib", "tempfile",
        # Networking
        "socket", "http", "urllib", "ssl", "requests", "ftplib",
        # System
        "subprocess", "multiprocessing", "ctypes", "threading",
        # Other
        "builtins", "sysconfig"
    }
