def optional_import(name: str):
    try:
        module = __import__(name)
        return module
    except Exception:
        return None
