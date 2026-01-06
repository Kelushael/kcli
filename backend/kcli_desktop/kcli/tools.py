"""Desktop Commander tools for KCLI."""

import os
import json
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class ToolRegistry:
    """Desktop Commander tool implementations."""
    
    def __init__(self, workspace: Path, logs_dir: Path):
        self.workspace = Path(workspace)
        self.logs_dir = Path(logs_dir)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.logs_dir / "tool_log.jsonl"
        self.processes: Dict[int, subprocess.Popen] = {}
    
    def _ensure_safe_path(self, path: str) -> Path:
        """Ensure path is within workspace."""
        target = (self.workspace / path).resolve()
        if self.workspace.resolve() not in target.parents and target != self.workspace.resolve():
            raise ValueError(f"Access denied: Path must be within workspace: {self.workspace}")
        return target
    
    def _log(self, tool: str, args: Dict, result: str):
        """Log tool execution."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool,
            "args": args,
            "result": result[:500]
        }
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def list_directory(self, path: str = "") -> List[Dict]:
        """List files and directories."""
        target = self._ensure_safe_path(path)
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
        
        items = []
        for entry in sorted(target.iterdir()):
            items.append({
                "name": entry.name,
                "path": str(entry.relative_to(self.workspace)),
                "is_dir": entry.is_dir(),
                "size": entry.stat().st_size if entry.is_file() else None
            })
        
        self._log("list_directory", {"path": path}, f"Found {len(items)} items")
        return items
    
    def read_file(self, path: str) -> str:
        """Read file contents."""
        target = self._ensure_safe_path(path)
        if not target.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not target.is_file():
            raise ValueError(f"Not a file: {path}")
        
        content = target.read_text(encoding='utf-8', errors='replace')
        self._log("read_file", {"path": path}, f"Read {len(content)} chars")
        return content
    
    def write_file(self, path: str, content: str) -> str:
        """Write content to file."""
        target = self._ensure_safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
        self._log("write_file", {"path": path}, f"Wrote {len(content)} chars")
        return f"Successfully wrote {len(content)} characters to {path}"
    
    def search_text(self, needle: str, path: str = "") -> List[Dict]:
        """Search for text in files."""
        target = self._ensure_safe_path(path)
        matches = []
        
        patterns = ['*.py', '*.js', '*.ts', '*.jsx', '*.tsx', '*.json', '*.md', '*.txt', '*.html', '*.css', '*.yaml', '*.yml']
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
        
        self._log("search_text", {"needle": needle}, f"Found {len(matches)} matches")
        return matches[:50]
    
    def edit_block(self, path: str, old_text: str, new_text: str) -> str:
        """Replace text block in file."""
        content = self.read_file(path)
        if old_text not in content:
            return f"Error: Pattern not found in {path}"
        
        updated = content.replace(old_text, new_text, 1)
        self.write_file(path, updated)
        self._log("edit_block", {"path": path}, "Block edited")
        return f"Successfully edited {path}"
    
    def create_directory(self, path: str) -> str:
        """Create a directory."""
        target = self._ensure_safe_path(path)
        target.mkdir(parents=True, exist_ok=True)
        self._log("create_directory", {"path": path}, "Directory created")
        return f"Created directory: {path}"
    
    def delete_file(self, path: str) -> str:
        """Delete a file."""
        target = self._ensure_safe_path(path)
        if not target.exists():
            return f"File not found: {path}"
        if target.is_dir():
            return "Cannot delete directory with this tool."
        target.unlink()
        self._log("delete_file", {"path": path}, "File deleted")
        return f"Deleted: {path}"
    
    def run_command(self, command: str, timeout: int = 30) -> Dict:
        """Run a shell command (sandboxed)."""
        # Whitelist safe commands
        safe_prefixes = ['echo', 'cat', 'ls', 'dir', 'pwd', 'date', 'whoami', 
                         'python --version', 'python -c', 'node --version', 
                         'pip list', 'pip show', 'git status', 'git log', 'git diff']
        is_safe = any(command.strip().lower().startswith(p) for p in safe_prefixes)
        
        if not is_safe:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command blocked for safety. Allowed prefixes: {', '.join(safe_prefixes[:5])}...",
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
            self._log("run_command", {"command": command}, f"Exit: {result.returncode}")
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
    
    def get_tool_definitions(self) -> str:
        """Get tool definitions for system prompt."""
        return """Available tools:
- list_directory(path): List files in a directory
- read_file(path): Read file contents  
- write_file(path, content): Write to a file
- search_text(needle, path): Search for text in files
- edit_block(path, old_text, new_text): Replace text in a file
- create_directory(path): Create a directory
- delete_file(path): Delete a file
- run_command(command): Run safe shell commands

To use a tool, respond with:
```tool
{"tool": "tool_name", "args": {"arg1": "value1"}}
```"""
