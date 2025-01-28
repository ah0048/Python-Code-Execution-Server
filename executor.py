import sys

globals_dict = {"__name__": "__main__"}
while True:
    try:
        # Read code from stdin
        code = input()
        exec(code, globals_dict)
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
