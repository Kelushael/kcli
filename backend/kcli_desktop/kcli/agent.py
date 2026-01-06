"""Main KCLI agent with CLI interface."""

import re
import json
import sys
from typing import List, Dict, Optional
from datetime import datetime

try:
    from colorama import Fore, Back, Style, init as colorama_init
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

from .config import KCLIConfig, WORKSPACE_DIR, LOGS_DIR
from .providers import ProviderManager
from .tools import ToolRegistry


# ASCII Banner
BANNER = r"""
╔══════════════════════════════════════════════════╗
║     _  _______ _     ___                    ║
║    | |/ / ____| |   |_ _|                   ║
║    | ' / |    | |    | |                    ║
║    | . \ |____| |___ | |                    ║
║    |_|\_\_____|_____|___|                   ║
║                                              ║
║         Desktop Commander v1.0              ║
║    AI-Powered Terminal Assistant            ║
╚══════════════════════════════════════════════════╝
"""

SYSTEM_PROMPT = """You are KCLI (Kelushael CLI), a powerful AI coding assistant with Desktop Commander capabilities.
You operate within a sandboxed workspace for safety.

{tools}

Always explain your plan before using tools. Be concise but helpful."""


class Agent:
    """Main KCLI agent."""
    
    def __init__(self, config: Optional[KCLIConfig] = None):
        if COLORAMA_AVAILABLE:
            colorama_init(autoreset=True)
        
        self.config = config or KCLIConfig.load()
        self.tools = ToolRegistry(self.config.workspace, str(LOGS_DIR))
        self.providers = ProviderManager(self.config)
        self.conversation: List[Dict[str, str]] = []
        self._init_system_prompt()
    
    def _init_system_prompt(self):
        """Initialize system prompt with tool definitions."""
        system_content = SYSTEM_PROMPT.format(tools=self.tools.get_tool_definitions())
        self.conversation = [{"role": "system", "content": system_content}]
    
    def _color(self, text: str, fore: str = "", back: str = "", style: str = "") -> str:
        """Apply color if colorama is available."""
        if not COLORAMA_AVAILABLE:
            return text
        prefix = ""
        if fore:
            prefix += getattr(Fore, fore.upper(), "")
        if back:
            prefix += getattr(Back, back.upper(), "")
        if style:
            prefix += getattr(Style, style.upper(), "")
        suffix = Style.RESET_ALL if prefix else ""
        return f"{prefix}{text}{suffix}"
    
    def print_banner(self):
        """Print welcome banner."""
        print(self._color(BANNER, fore="cyan"))
        print(self._color(f"  Provider: {self.providers.current_name}", fore="yellow"))
        print(self._color(f"  Model: {self.config.model}", fore="yellow"))
        print(self._color(f"  Workspace: {self.config.workspace}", fore="yellow"))
        api_status = "Connected" if self.config.api_key else "Not configured (demo mode)"
        color = "green" if self.config.api_key else "red"
        print(self._color(f"  API: {api_status}", fore=color))
        print()
        print(self._color("  Commands: /help /provider /model /exit", fore="white", style="dim"))
        print(self._color("  " + "="*48, fore="cyan"))
        print()
    
    def extract_tool_calls(self, text: str) -> List[Dict]:
        """Extract tool calls from AI response."""
        calls = []
        
        # Match ```tool ... ``` blocks
        blocks = re.findall(r'```tool\s*([\s\S]*?)```', text, re.IGNORECASE)
        for block in blocks:
            try:
                call = json.loads(block.strip())
                if "tool" in call:
                    calls.append(call)
            except json.JSONDecodeError:
                continue
        
        # Match [[TOOL_CALL:...]] format
        inline = re.findall(r'\[\[TOOL_CALL:([^\]]+)\]\]', text)
        for entry in inline:
            try:
                calls.append(json.loads(entry.strip()))
            except json.JSONDecodeError:
                continue
        
        return calls
    
    def approve_tool(self, tool_call: Dict) -> bool:
        """Ask user to approve tool execution."""
        if self.config.auto_approve:
            return True
        
        print()
        print(self._color("┌─ TOOL EXECUTION REQUEST ─────────────────────", fore="magenta"))
        print(self._color(f"│ Tool: {tool_call.get('tool')}", fore="yellow"))
        print(self._color("│ Args:", fore="white"))
        for key, val in tool_call.get('args', {}).items():
            val_str = str(val)[:60] + "..." if len(str(val)) > 60 else str(val)
            print(self._color(f"│   {key}: {val_str}", fore="white", style="dim"))
        print(self._color("└───────────────────────────────────────────", fore="magenta"))
        
        try:
            response = input(self._color("Approve? [y/N]: ", fore="cyan")).strip().lower()
            return response in ('y', 'yes')
        except (KeyboardInterrupt, EOFError):
            return False
    
    def execute_tool(self, tool_call: Dict) -> str:
        """Execute a tool and return result."""
        tool = tool_call.get("tool")
        args = tool_call.get("args", {})
        
        try:
            if tool == "list_directory":
                result = self.tools.list_directory(args.get("path", ""))
                return json.dumps(result, indent=2)
            elif tool == "read_file":
                return self.tools.read_file(args["path"])
            elif tool == "write_file":
                return self.tools.write_file(args["path"], args["content"])
            elif tool == "search_text":
                result = self.tools.search_text(args["needle"], args.get("path", ""))
                return json.dumps(result, indent=2)
            elif tool == "edit_block":
                return self.tools.edit_block(args["path"], args["old_text"], args["new_text"])
            elif tool == "create_directory":
                return self.tools.create_directory(args["path"])
            elif tool == "delete_file":
                return self.tools.delete_file(args["path"])
            elif tool == "run_command":
                result = self.tools.run_command(args["command"], args.get("timeout", 30))
                return json.dumps(result, indent=2)
            else:
                return f"Unknown tool: {tool}"
        except Exception as e:
            return f"Tool error: {e}"
    
    def handle_command(self, command: str) -> bool:
        """Handle slash commands. Returns True if should exit."""
        parts = command.split()
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        if cmd == "/exit" or cmd == "/quit":
            print(self._color("Goodbye!", fore="cyan"))
            return True
        
        elif cmd == "/help":
            print(self._color("\nCommands:", fore="cyan"))
            print("  /help              - Show this help")
            print("  /provider [name]   - Show or switch provider")
            print("  /model [name]      - Show or set model")
            print("  /config            - Show configuration")
            print("  /clear             - Clear conversation")
            print("  /exit              - Exit KCLI")
            print()
        
        elif cmd == "/provider":
            if args:
                name = args[0]
                if self.providers.switch(name):
                    self.config.save()
                    print(self._color(f"Switched to {name}", fore="green"))
                else:
                    print(self._color(f"Unknown provider. Available: {', '.join(self.providers.list_providers())}", fore="red"))
            else:
                print(self._color(f"Current: {self.providers.current_name}", fore="yellow"))
                print(f"Available: {', '.join(self.providers.list_providers())}")
        
        elif cmd == "/model":
            if args:
                self.config.model = args[0]
                self.config.save()
                print(self._color(f"Model set to: {args[0]}", fore="green"))
            else:
                print(self._color(f"Current model: {self.config.model}", fore="yellow"))
        
        elif cmd == "/config":
            print(self._color("\nConfiguration:", fore="cyan"))
            print(f"  Provider: {self.config.provider}")
            print(f"  Model: {self.config.model}")
            print(f"  Base URL: {self.config.base_url}")
            print(f"  Workspace: {self.config.workspace}")
            print(f"  API Key: {'***' + self.config.api_key[-4:] if self.config.api_key else 'Not set'}")
            print()
        
        elif cmd == "/clear":
            self._init_system_prompt()
            print(self._color("Conversation cleared.", fore="green"))
        
        else:
            print(self._color(f"Unknown command: {cmd}", fore="red"))
        
        return False
    
    def chat(self, user_input: str) -> str:
        """Process user input and get AI response."""
        self.conversation.append({"role": "user", "content": user_input})
        
        response = self.providers.chat(self.conversation)
        self.conversation.append({"role": "assistant", "content": response})
        
        return response
    
    def run(self):
        """Main interactive loop."""
        self.print_banner()
        
        while True:
            try:
                prompt = self._color("KCLI> ", fore="cyan", style="bright")
                user_input = input(prompt).strip()
            except (KeyboardInterrupt, EOFError):
                print(self._color("\nGoodbye!", fore="cyan"))
                break
            
            if not user_input:
                continue
            
            # Handle slash commands
            if user_input.startswith("/"):
                if self.handle_command(user_input):
                    break
                continue
            
            # Get AI response
            print(self._color("\nThinking...", fore="yellow", style="dim"))
            response = self.chat(user_input)
            
            # Display response
            print()
            print(self._color("┌─ KCLI ─────────────────────────────────────", fore="green"))
            for line in response.split("\n"):
                print(self._color(f"│ {line}", fore="white"))
            print(self._color("└" + "─"*43, fore="green"))
            
            # Check for tool calls
            tool_calls = self.extract_tool_calls(response)
            for call in tool_calls:
                if self.approve_tool(call):
                    print(self._color("\nExecuting...", fore="yellow"))
                    result = self.execute_tool(call)
                    
                    # Add tool result to conversation
                    self.conversation.append({"role": "tool", "content": result})
                    
                    # Display result
                    print(self._color("┌─ TOOL RESULT ────────────────────────────", fore="blue"))
                    for line in result.split("\n")[:30]:
                        print(self._color(f"│ {line}", fore="white", style="dim"))
                    if len(result.split("\n")) > 30:
                        print(self._color("│ ... (truncated)", fore="white", style="dim"))
                    print(self._color("└" + "─"*43, fore="blue"))
                else:
                    print(self._color("Tool execution cancelled.", fore="red"))
            
            print()


def main():
    """Entry point."""
    agent = Agent()
    agent.run()


if __name__ == "__main__":
    main()
