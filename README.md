# TabTabTab MCP Server

Model Context Protocol (MCP) server for integration with Cursor and other MCP clients.

## Overview

This is a standalone MCP protocol server that allows AI assistants like Cursor to interact with Google Sheets through the MCP protocol. It wraps the Background API's HTTP endpoints and exposes them as MCP tools.

## Components

- **`server.py`** - MCP protocol server implementation
  - Implements MCP stdio protocol
  - Provides `edit_google_sheet` tool
  - Handles streaming HTTP → MCP tool response conversion

- **`cursor_mcp_config.json`** - Configuration for Cursor IDE
  - Contains the MCP server settings
  - Specifies Python interpreter path and server script location
  - Includes environment variables (API keys, server URL)
  - Make sure `python` exists in the environment and has the `mcp` library installed

## Setup

### 1. Configure Environment Variables

The server needs these environment variables (set in `cursor_mcp_config.json`):

- `TABTABTAB_API_KEY` - Your API key for authentication with the backend
- `TABTABTAB_SERVER_URL` - Backend server URL (default: `http://localhost:8000`)

### 2. Add to Cursor Settings

Copy the contents of `cursor_mcp_config.json` to your Cursor MCP settings:

**macOS/Linux:** `~/.cursor/mcp_settings.json`  
**Windows:** `%APPDATA%\Cursor\mcp_settings.json`

Or use Cursor's Settings UI: **Cursor Settings** → **Features** → **Model Context Protocol**

### 3. Restart Cursor

After adding the configuration, restart Cursor for the changes to take effect.

## Usage in Cursor

Once configured, you can use the MCP tool in Cursor's AI chat:

```
Add research about top AI code editors to my Google Sheet
```

The AI will automatically use the `edit_google_sheet` tool with the appropriate parameters.

## Tool Schema

### `edit_google_sheet`

Edit a Google Sheet using an AI agent.

**Parameters:**
- `prompt` (string, required) - The instruction for editing the sheet
- `google_access_token` (string, required) - Google OAuth 2.0 access token
- `spreadsheet_id` (string, required) - The Google Sheets spreadsheet ID
- `conversation_id` (string, optional) - Conversation ID to continue existing conversation
- `model` (string, optional) - Model to use (defaults to Claude Haiku 4.5)

**Returns:**
- Progress updates during execution
- Final success/error message
- Conversation ID for follow-up requests
- Turn count and completion status