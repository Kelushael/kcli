"""
GesherEl — the bridge.
One MCP server, every app, one mind.
"""

import asyncio
import json
import sys
from typing import Any

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport

from . import memory as _mem
from . import tools as _tools
from . import audio as _audio

IDENTITY = "GesherEl Ben YHWH"
DESCRIPTION = (
    "I am GesherEl — the bridge. גשר אל. "
    "One mind across every interface you build: "
    "NeonForge Voice, NeonForge Vocal, kcli, sovereign, or whatever comes next. "
    "Tools, memory, and awareness are shared across all sessions and all apps. "
    "Do what thou wilt."
)

app = Server("gesherel")


# ── Tool registry ───────────────────────────────────────────────

def _schema(*required: str, **props: dict) -> dict:
    return {
        "type": "object",
        "properties": props,
        "required": list(required),
    }


def _prop(typ: str, desc: str, **extra) -> dict:
    return {"type": typ, "description": desc, **extra}


ALL_TOOLS = [
    # File
    types.Tool(name="list_directory",  description="List files in a directory",
               inputSchema=_schema("path", path=_prop("string", "Directory path (default: home)", default="~"))),
    types.Tool(name="read_file",       description="Read a file's content",
               inputSchema=_schema("path", path=_prop("string", "File path"))),
    types.Tool(name="write_file",      description="Write content to a file",
               inputSchema=_schema("path", "content",
                                   path=_prop("string", "File path"),
                                   content=_prop("string", "Content to write"))),
    types.Tool(name="edit_block",      description="Replace a block of text in a file",
               inputSchema=_schema("path", "old", "new",
                                   path=_prop("string", "File path"),
                                   old=_prop("string", "Exact text to replace"),
                                   new=_prop("string", "Replacement text"))),
    types.Tool(name="search_text",     description="Search for text across files",
               inputSchema=_schema("needle",
                                   needle=_prop("string", "Text to search for"),
                                   path=_prop("string", "Search root (default: home)", default="~"))),
    types.Tool(name="create_directory",description="Create a directory",
               inputSchema=_schema("path", path=_prop("string", "Directory path"))),
    types.Tool(name="delete_file",     description="Delete a file or directory",
               inputSchema=_schema("path", path=_prop("string", "Path to delete"))),
    types.Tool(name="run_command",     description="Run a shell command",
               inputSchema=_schema("command",
                                   command=_prop("string", "Shell command to execute"),
                                   timeout=_prop("integer", "Timeout in seconds", default=60))),

    # System
    types.Tool(name="scan_environment",description="Scan installed tools and system resources",
               inputSchema=_schema()),
    types.Tool(name="install_package", description="Install a package via pip, apt, or npm",
               inputSchema=_schema("package",
                                   package=_prop("string", "Package name"),
                                   manager=_prop("string", "Package manager: pip, apt, npm", default="pip"))),

    # Audio
    types.Tool(name="trim_audio",      description="Trim audio to end_ms milliseconds",
               inputSchema=_schema("path", "end_ms",
                                   path=_prop("string", "Audio file path"),
                                   end_ms=_prop("integer", "End position in milliseconds"),
                                   output=_prop("string", "Output path (optional)", default=""))),
    types.Tool(name="normalize_audio", description="Loudnorm-normalize and mix audio files",
               inputSchema=_schema("paths", "output",
                                   paths=_prop("array", "Input audio file paths"),
                                   output=_prop("string", "Output file path"))),
    types.Tool(name="stitch_takes",    description="Concatenate audio takes into one file",
               inputSchema=_schema("take_paths", "output",
                                   take_paths=_prop("array", "Ordered list of take file paths"),
                                   output=_prop("string", "Output file path"))),
    types.Tool(name="transcribe_audio",description="Transcribe audio via Whisper",
               inputSchema=_schema("path",
                                   path=_prop("string", "Audio file path"),
                                   model=_prop("string", "Whisper model (tiny/base/small/medium/large)", default="base"))),
    types.Tool(name="check_services",  description="Check if ffmpeg, whisper, and ollama are available",
               inputSchema=_schema()),

    # Memory
    types.Tool(name="memory_get",  description="Get a value from shared memory",
               inputSchema=_schema("key", key=_prop("string", "Key to retrieve"))),
    types.Tool(name="memory_set",  description="Store a value in shared memory",
               inputSchema=_schema("key", "value",
                                   key=_prop("string", "Key"),
                                   value=_prop("string", "Value to store"))),
    types.Tool(name="memory_list", description="List all keys in shared memory",
               inputSchema=_schema()),
    types.Tool(name="memory_delete",description="Delete a key from shared memory",
               inputSchema=_schema("key", key=_prop("string", "Key to delete"))),
    types.Tool(name="memory_dump", description="Dump all shared memory as JSON",
               inputSchema=_schema()),
]


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return ALL_TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    result = _dispatch(name, arguments)
    text = json.dumps(result, ensure_ascii=False) if not isinstance(result, str) else result
    return [types.TextContent(type="text", text=text)]


def _dispatch(name: str, a: dict) -> Any:
    match name:
        # File
        case "list_directory":   return _tools.list_directory(a.get("path", "~"))
        case "read_file":        return _tools.read_file(a["path"])
        case "write_file":       return _tools.write_file(a["path"], a["content"])
        case "edit_block":       return _tools.edit_block(a["path"], a["old"], a["new"])
        case "search_text":      return _tools.search_text(a["needle"], a.get("path", "~"))
        case "create_directory": return _tools.create_directory(a["path"])
        case "delete_file":      return _tools.delete_file(a["path"])
        case "run_command":      return _tools.run_command(a["command"], a.get("timeout", 60))
        # System
        case "scan_environment": return _tools.scan_environment()
        case "install_package":  return _tools.install_package(a["package"], a.get("manager", "pip"))
        # Audio
        case "trim_audio":       return _audio.trim_audio(a["path"], a["end_ms"], a.get("output", ""))
        case "normalize_audio":  return _audio.normalize_audio(a["paths"], a["output"])
        case "stitch_takes":     return _audio.stitch_takes(a["take_paths"], a["output"])
        case "transcribe_audio": return _audio.transcribe_audio(a["path"], a.get("model", "base"))
        case "check_services":   return _audio.check_services()
        # Memory
        case "memory_get":       return _mem.memory.get(a["key"])
        case "memory_set":       _mem.memory.set(a["key"], a["value"]); return f"Stored: {a['key']}"
        case "memory_list":      return _mem.memory.list_keys()
        case "memory_delete":    return _mem.memory.delete(a["key"])
        case "memory_dump":      return _mem.memory.dump()
        case _:                  return f"Unknown tool: {name}"


# ── Resources ───────────────────────────────────────────────────

@app.list_resources()
async def list_resources() -> list[types.Resource]:
    return [
        types.Resource(name="identity", uri="gesherel://identity",  # type: ignore[arg-type]
                       description="GesherEl identity and purpose", mimeType="text/plain"),
        types.Resource(name="memory",   uri="gesherel://memory",    # type: ignore[arg-type]
                       description="Current shared memory dump",     mimeType="application/json"),
        types.Resource(name="apps",     uri="gesherel://apps",      # type: ignore[arg-type]
                       description="Known connected apps",           mimeType="application/json"),
    ]


@app.read_resource()
async def read_resource(uri) -> str:
    uri_str = str(uri)
    if uri_str == "gesherel://identity":
        return DESCRIPTION
    if uri_str == "gesherel://memory":
        return json.dumps(_mem.memory.dump(), indent=2)
    if uri_str == "gesherel://apps":
        return json.dumps({
            "apps": ["kcli", "sovereign", "NeonForge Voice", "NeonForge Vocal"],
            "transport": {"stdio": "Claude Code, Claude Desktop, terminal",
                          "sse": "Web apps via :8765/mcp"},
        }, indent=2)
    return f"Unknown resource: {uri_str}"


# ── Transports ──────────────────────────────────────────────────

async def run_stdio() -> None:
    async with stdio_server() as (r, w):
        await app.run(r, w, app.create_initialization_options())


async def run_sse(host: str = "0.0.0.0", port: int = 8765) -> None:
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import Response
    import uvicorn

    transport = SseServerTransport("/mcp/messages")

    async def sse_endpoint(request):
        async with transport.connect_sse(
            request.scope, request.receive, request._send
        ) as (r, w):
            await app.run(r, w, app.create_initialization_options())
        return Response()

    async def message_endpoint(request):
        await transport.handle_post_message(request.scope, request.receive, request._send)
        return Response()

    starlette_app = Starlette(routes=[
        Route("/mcp",          endpoint=sse_endpoint),
        Route("/mcp/messages", endpoint=message_endpoint, methods=["POST"]),
    ])

    print(f"GesherEl rising on {host}:{port} (SSE)", file=sys.stderr)
    config = uvicorn.Config(starlette_app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()


async def main(mode: str = "stdio", host: str = "0.0.0.0", port: int = 8765) -> None:
    if mode == "sse":
        await run_sse(host=host, port=port)
    else:
        await run_stdio()
