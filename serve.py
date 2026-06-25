#!/usr/bin/env python3
"""Entry point for the store-preview backend.

The implementation lives in the `server` package (split by concern: stores,
project, android, ios, preview, http_app). This stays a thin shim so the
existing contracts keep working:

  • run.sh / launch.json:  `python3 serve.py [PORT]`
  • desktop sidecar:       `import serve; serve.run()`

Runtime config (SP_ROOT, PORT) is read from the environment by server.context
at import time — set those BEFORE importing this module, as the sidecar does.
"""
from server.http_app import Handler, run

__all__ = ["Handler", "run"]

if __name__ == "__main__":
    run()
