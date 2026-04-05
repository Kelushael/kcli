from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import httpx
import json
import subprocess
import asyncio
import re

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# OpenRouter config
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
# sovereign: api-key-check
if not OPENROUTER_API_KEY:
    import warnings
    warnings.warn("OPENROUTER_API_KEY is not set. Chat will return errors.", stacklevel=1)

OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'cognitivecomputations/dolphin-mistral-24b-venice-edition:free')
OPENROUTER_BASE_URL = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')

# Workspace for file operations (sandboxed)
WORKSPACE_DIR = ROOT_DIR / 'workspace'
WORKSPACE_DIR.mkdir(exist_ok=True)

app = FastAPI(title="KCLI Agent - Desktop Commander")
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============== MODELS ==============

class ChatMessage(BaseModel):
    role: str  # 'user', 'assistant', 'system', 'tool'
    content: str
    tool_call: Optional[Dict[str, Any]] = None
    tool_result: Optional[str] = None

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None

class ChatResponse(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    response: str
    tool_calls: List[Dict[str, Any]] = []
    model_used: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ToolExecuteRequest(BaseModel):
    tool: str
    args: Dict[str, Any]
    approved: bool = False

class ToolExecuteResponse(BaseModel):
    success: bool
    result: str
    tool: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"

class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    messages: List[Dict[str, Any]] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class FileItem(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: Optional[int] = None

class ProcessInfo(BaseModel):
    pid: int
    command: str
    status: str

# ============== TOOL REGISTRY ==============

class ToolRegistry:
    """Desktop Commander tool implementations - sandboxed to workspace."""
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.processes: Dict[int, subprocess.Popen] = {}
        self.tool_log: List[Dict] = []
    
    def _ensure_safe_path(self, path: str) -> Path:
        """Ensure path stays within workspace."""
        target = (self.workspace / path).resolve()
        if self.workspace not in target.parents and target != self.workspace:
            raise ValueError(f"Access denied: Path must be within workspace")
        return target
    
    def _log_tool(self, tool: str, args: Dict, result: str):
        self.tool_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "args": args,
            "result": result[:500]  # Truncate for logging
        })
    
    def list_directory(self, path: str = "") -> List[Dict]:
        """List files and directories."""
        target = self._ensure_safe_path(path)
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
        
        items = []
        for entry in target.iterdir():
            items.append({
                "name": entry.name,
                "path": str(entry.relative_to(self.workspace)),
                "is_dir": entry.is_dir(),
                "size": entry.stat().st_size if entry.is_file() else None
            })
        
        self._log_tool("list_directory", {"path": path}, f"Found {len(items)} items")
        return items
    
    def read_file(self, path: str) -> str:
        """Read file contents."""
        target = self._ensure_safe_path(path)
        if not target.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not target.is_file():
            raise ValueError(f"Not a file: {path}")
        
        content = target.read_text(encoding='utf-8', errors='replace')
        self._log_tool("read_file", {"path": path}, f"Read {len(content)} chars")
        return content
    
    def write_file(self, path: str, content: str) -> str:
        """Write content to file."""
        target = self._ensure_safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
        self._log_tool("write_file", {"path": path}, f"Wrote {len(content)} chars")
        return f"Successfully wrote {len(content)} characters to {path}"
    
    def search_text(self, needle: str, path: str = "") -> List[Dict]:
        """Search for text in files."""
        target = self._ensure_safe_path(path)
        matches = []
        
        patterns = ['*.py', '*.js', '*.ts', '*.jsx', '*.tsx', '*.json', '*.md', '*.txt', '*.html', '*.css']
        for pattern in patterns:
            for file_path in target.rglob(pattern):
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    if needle.lower() in content.lower():
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if needle.lower() in line.lower():
                                matches.append({
                                    "file": str(file_path.relative_to(self.workspace)),
                                    "line": i + 1,
                                    "content": line.strip()[:200]
                                })
                except Exception:
                    continue
        
        self._log_tool("search_text", {"needle": needle, "path": path}, f"Found {len(matches)} matches")
        return matches[:50]  # Limit results
    
    def edit_block(self, path: str, old_text: str, new_text: str) -> str:
        """Replace text block in file."""
        content = self.read_file(path)
        if old_text not in content:
            return f"Error: Pattern not found in {path}"
        
        updated = content.replace(old_text, new_text, 1)
        self.write_file(path, updated)
        self._log_tool("edit_block", {"path": path}, "Block edited successfully")
        return f"Successfully edited {path}"
    
    def create_directory(self, path: str) -> str:
        """Create a directory."""
        target = self._ensure_safe_path(path)
        target.mkdir(parents=True, exist_ok=True)
        self._log_tool("create_directory", {"path": path}, "Directory created")
        return f"Created directory: {path}"
    
    def delete_file(self, path: str) -> str:
        """Delete a file."""
        target = self._ensure_safe_path(path)
        if not target.exists():
            return f"File not found: {path}"
        if target.is_dir():
            return f"Cannot delete directory with this tool. Use delete_directory."
        target.unlink()
        self._log_tool("delete_file", {"path": path}, "File deleted")
        return f"Deleted: {path}"
    
    def run_command(self, command: str, timeout: int = 30) -> Dict:
        """Run a shell command (sandboxed, limited commands)."""
        # Whitelist safe commands
        safe_prefixes = ['echo', 'cat', 'ls', 'dir', 'pwd', 'date', 'whoami', 'python --version', 'node --version', 'pip list']
        is_safe = any(command.strip().lower().startswith(p) for p in safe_prefixes)
        
        if not is_safe:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command not allowed for safety. Allowed: {', '.join(safe_prefixes)}",
                "return_code": -1
            }
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.workspace)
            )
            self._log_tool("run_command", {"command": command}, f"Exit code: {result.returncode}")
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[:5000],
                "stderr": result.stderr[:1000],
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": "", "stderr": "Command timed out", "return_code": -1}
        except Exception as e:
            return {"success": False, "stdout": "", "stderr": str(e), "return_code": -1}
    
    def get_tool_log(self) -> List[Dict]:
        """Return recent tool execution log."""
        return self.tool_log[-50:]

# Initialize tool registry
tools = ToolRegistry(WORKSPACE_DIR)

# ============== OPENROUTER PROVIDER ==============

SYSTEM_PROMPT = """You are KCLI (Kelushael CLI), a powerful AI coding assistant with Desktop Commander capabilities.

You have access to these tools:
- list_directory(path): List files in a directory
- read_file(path): Read file contents
- write_file(path, content): Write to a file
- search_text(needle, path): Search for text in files
- edit_block(path, old_text, new_text): Replace text in a file
- create_directory(path): Create a directory
- delete_file(path): Delete a file
- run_command(command): Run safe shell commands

When you need to use a tool, respond with a JSON block like this:
```tool
{"tool": "tool_name", "args": {"arg1": "value1"}}
```

Always explain your plan before suggesting tool usage. Be concise but helpful.
You operate within a sandboxed workspace for safety."""

async def call_openrouter(messages: List[Dict], model: str = None) -> str:
    """Call OpenRouter API."""
    if not OPENROUTER_API_KEY:
        return "Error: OpenRouter API key not configured."
    
    model = model or OPENROUTER_MODEL
    
    # Convert messages to OpenRouter format
    formatted_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in messages:
        formatted_messages.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", "")
        })
    
    payload = {
        "model": model,
        "messages": formatted_messages[-25:],  # Keep context manageable
        "stream": False
    }
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://kcli-agent.local",
        "X-Title": "KCLI Desktop Commander"
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except httpx.HTTPStatusError as e:
        logger.error(f"OpenRouter API error: {e.response.text}")
        return f"API Error: {e.response.status_code} - {e.response.text[:200]}"
    except Exception as e:
        logger.error(f"OpenRouter call failed: {e}")
        return f"Error calling AI: {str(e)}"

def extract_tool_calls(text: str) -> List[Dict]:
    """Extract tool calls from AI response."""
    tool_calls = []
    
    # Match ```tool ... ``` blocks
    tool_blocks = re.findall(r'```tool\s*([\s\S]*?)```', text, re.IGNORECASE)
    for block in tool_blocks:
        try:
            call = json.loads(block.strip())
            if "tool" in call:
                tool_calls.append(call)
        except json.JSONDecodeError:
            continue
    
    # Match [[TOOL_CALL:...]] format
    inline_calls = re.findall(r'\[\[TOOL_CALL:([^\]]+)\]\]', text)
    for call in inline_calls:
        try:
            tool_calls.append(json.loads(call.strip()))
        except json.JSONDecodeError:
            continue
    
    return tool_calls

# ============== API ROUTES ==============

@api_router.get("/")
async def root():
    return {"message": "KCLI Agent API", "status": "online", "model": OPENROUTER_MODEL}

@api_router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message to the AI agent."""
    messages = [msg.model_dump() for msg in request.messages]
    model = request.model or OPENROUTER_MODEL
    
    response_text = await call_openrouter(messages, model)
    tool_calls = extract_tool_calls(response_text)
    
    return ChatResponse(
        response=response_text,
        tool_calls=tool_calls,
        model_used=model
    )

@api_router.post("/tools/execute", response_model=ToolExecuteResponse)
async def execute_tool(request: ToolExecuteRequest):
    """Execute a tool with approval."""
    if not request.approved:
        raise HTTPException(status_code=400, detail="Tool execution requires approval")
    
    tool_name = request.tool
    args = request.args
    
    try:
        if tool_name == "list_directory":
            result = tools.list_directory(args.get("path", ""))
            return ToolExecuteResponse(success=True, result=json.dumps(result, indent=2), tool=tool_name)
        
        elif tool_name == "read_file":
            result = tools.read_file(args["path"])
            return ToolExecuteResponse(success=True, result=result, tool=tool_name)
        
        elif tool_name == "write_file":
            result = tools.write_file(args["path"], args["content"])
            return ToolExecuteResponse(success=True, result=result, tool=tool_name)
        
        elif tool_name == "search_text":
            result = tools.search_text(args["needle"], args.get("path", ""))
            return ToolExecuteResponse(success=True, result=json.dumps(result, indent=2), tool=tool_name)
        
        elif tool_name == "edit_block":
            result = tools.edit_block(args["path"], args["old_text"], args["new_text"])
            return ToolExecuteResponse(success=True, result=result, tool=tool_name)
        
        elif tool_name == "create_directory":
            result = tools.create_directory(args["path"])
            return ToolExecuteResponse(success=True, result=result, tool=tool_name)
        
        elif tool_name == "delete_file":
            result = tools.delete_file(args["path"])
            return ToolExecuteResponse(success=True, result=result, tool=tool_name)
        
        elif tool_name == "run_command":
            result = tools.run_command(args["command"], args.get("timeout", 30))
            return ToolExecuteResponse(success=result["success"], result=json.dumps(result, indent=2), tool=tool_name)
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")
    
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return ToolExecuteResponse(success=False, result=str(e), tool=tool_name)

@api_router.get("/tools/log")
async def get_tool_log():
    """Get recent tool execution log."""
    return {"log": tools.get_tool_log()}

@api_router.get("/files")
async def list_files(path: str = ""):
    """List files in workspace."""
    try:
        items = tools.list_directory(path)
        return {"items": items, "path": path}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.get("/files/read")
async def read_file_content(path: str):
    """Read a file from workspace."""
    try:
        content = tools.read_file(path)
        return {"content": content, "path": path}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.post("/files/write")
async def write_file_content(path: str, content: str):
    """Write to a file in workspace."""
    try:
        result = tools.write_file(path, content)
        return {"result": result, "path": path}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Conversations CRUD
@api_router.post("/conversations", response_model=Conversation)
async def create_conversation(data: ConversationCreate):
    conv = Conversation(title=data.title)
    doc = conv.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.conversations.insert_one(doc)
    return conv

@api_router.get("/conversations")
async def list_conversations():
    convs = await db.conversations.find({}, {"_id": 0}).sort("updated_at", -1).to_list(100)
    return {"conversations": convs}

@api_router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    conv = await db.conversations.find_one({"id": conv_id}, {"_id": 0})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv

@api_router.put("/conversations/{conv_id}/messages")
async def add_message(conv_id: str, message: ChatMessage):
    msg_dict = message.model_dump()
    msg_dict['timestamp'] = datetime.now(timezone.utc).isoformat()
    
    result = await db.conversations.update_one(
        {"id": conv_id},
        {
            "$push": {"messages": msg_dict},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"success": True}

@api_router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    result = await db.conversations.delete_one({"id": conv_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"success": True}

@api_router.get("/config")
async def get_config():
    """Get current agent configuration."""
    return {
        "model": OPENROUTER_MODEL,
        "provider": "openrouter",
        "workspace": str(WORKSPACE_DIR),
        "api_configured": bool(OPENROUTER_API_KEY)
    }

@api_router.get("/download/kcli")
async def download_kcli():
    """Download KCLI Desktop package."""
    zip_path = WORKSPACE_DIR / "kcli_desktop.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Download not available")
    return FileResponse(
        path=str(zip_path),
        filename="kcli_desktop.zip",
        media_type="application/zip"
    )

@api_router.get("/download/install-script")
async def download_install_script():
    """Get the PowerShell install script content."""
    script_path = ROOT_DIR / "kcli_desktop" / "install.ps1"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="Install script not available")
    return FileResponse(
        path=str(script_path),
        filename="install.ps1",
        media_type="text/plain"
    )

# Include router and middleware
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://localhost:8080').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
