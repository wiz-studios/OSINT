from __future__ import annotations

# Backwards-compatible launcher. `.env` is loaded automatically if present.
from wiretapper.app import main

if __name__ == "__main__":
    raise SystemExit(main())
