from typing import Dict, Any, Optional, Set

def restricted_import(
    name: str,
    globals: Optional[Dict] = None,
    locals: Optional[Dict] = None,
    fromlist: tuple = (),
    level: int = 0
) -> Any:
    """Custom import function that blocks access to restricted modules."""
    from app.config import Config
    
    if name in Config.RESTRICTED_MODULES:
        raise PermissionError(f"Importing '{name}' is restricted for security reasons.")
    return __builtins__["__import__"](name, globals, locals, fromlist, level)

def create_restricted_environment() -> Dict[str, Any]:
    """Create a restricted execution environment with limited built-in functions."""
    safe_builtins = {
        # Mathematical operations
        "abs": abs, "divmod": divmod, "pow": pow, "round": round,
        # Type conversions
        "bool": bool, "int": int, "float": float, "str": str,
        # Data structures
        "list": list, "dict": dict, "set": set, "tuple": tuple,
        # Iterables and sequences
        "enumerate": enumerate, "filter": filter, "map": map, "zip": zip,
        "range": range, "reversed": reversed, "sorted": sorted,
        # Other safe operations
        "len": len, "max": max, "min": min, "sum": sum,
        "print": print, "isinstance": isinstance,
        # Custom restricted import
        "__import__": restricted_import
    }
    return {"__builtins__": safe_builtins}
