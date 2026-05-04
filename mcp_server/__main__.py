import asyncio
import sys

from .server import main

mode = "sse" if "--sse" in sys.argv else "stdio"

port = 8765
for arg in sys.argv:
    if arg.startswith("--port="):
        port = int(arg.split("=")[1])

asyncio.run(main(mode=mode, port=port))
