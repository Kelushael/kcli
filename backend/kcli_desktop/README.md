# KCLI Desktop Commander

```
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
```

An all-in-one AI coding agent with Desktop Commander capabilities. Like Codex CLI, but using free cloud APIs or local models!

## Features

- 🤖 **AI-Powered** - Chat with AI to write code, manage files, run commands
- 🛠️ **Desktop Commander Tools** - File operations, search, edit, process control
- 🔒 **Approval Gating** - AI proposes actions, you approve before execution
- 🌐 **Multi-Provider** - OpenRouter, Ollama, llama.cpp, or custom endpoints
- 🆓 **Free Models** - Works with free cloud APIs like OpenRouter free tier
- 📦 **Sandboxed** - All file operations restricted to workspace directory

## Quick Install (Windows)

### Option 1: Run the Installer
```powershell
# Download and run installer
irm https://raw.githubusercontent.com/kelushael/kcli/main/install.ps1 | iex
```

### Option 2: Install with pip
```powershell
pip install kcli
kcli
```

### Option 3: Install from Source
```powershell
git clone https://github.com/kelushael/kcli.git
cd kcli
pip install -e .
kcli
```

## First-Time Setup

1. Get a free API key from [OpenRouter](https://openrouter.ai/keys)
2. Run KCLI and set your key:

```
KCLI> /config
```

Or set environment variable:
```powershell
$env:OPENROUTER_API_KEY = "your-key-here"
kcli
```

## Usage

```
KCLI> List all files in the workspace
KCLI> Create a Python script that downloads a webpage
KCLI> Search for TODO comments in my code
KCLI> Edit the main.py file to add error handling
```

### Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/provider [name]` | Switch AI provider (openrouter, ollama, llamacpp) |
| `/model [name]` | Set the model to use |
| `/config` | Show current configuration |
| `/clear` | Clear conversation history |
| `/exit` | Exit KCLI |

### Available Tools

- `list_directory(path)` - List files in a directory
- `read_file(path)` - Read file contents
- `write_file(path, content)` - Write to a file
- `search_text(needle, path)` - Search for text in files
- `edit_block(path, old_text, new_text)` - Replace text in a file
- `create_directory(path)` - Create a directory
- `delete_file(path)` - Delete a file
- `run_command(command)` - Run safe shell commands

## Configuration

Config is stored in `~/.kcli/config.json`

```json
{
  "provider": "openrouter",
  "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
  "api_key": "your-key",
  "base_url": "https://openrouter.ai/api/v1",
  "workspace": "~/.kcli/workspace",
  "auto_approve": false
}
```

### Environment Variables

- `KCLI_PROVIDER` - AI provider (openrouter, ollama, llamacpp)
- `KCLI_MODEL` - Model name
- `KCLI_API_KEY` or `OPENROUTER_API_KEY` - API key
- `KCLI_BASE_URL` - API base URL
- `OLLAMA_HOST` - Ollama server URL
- `LLAMACPP_BASE_URL` - llama.cpp server URL

## Building Standalone Executable

```powershell
# Install build dependencies
pip install pyinstaller

# Build single .exe file
pyinstaller --onefile --name kcli --icon=assets/kcli.ico kcli/__main__.py

# The executable will be in dist/kcli.exe
```

## Building Installer

See `installer/README.md` for instructions on building a proper setup wizard.

## License

MIT License - See LICENSE file
