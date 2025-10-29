#!/usr/bin/env python3
"""MCP Protocol Server for Google Sheets

This is a proper MCP protocol server that can be used with Cursor, Claude Desktop,
or any other MCP client. It wraps our HTTP API and implements the MCP stdio protocol.

Usage:
    python mcp_protocol_server.py

Configuration for Cursor (add to MCP settings):
    {
        "mcpServers": {
            "google-sheets": {
                "command": "python",
                "args": ["/path/to/backend/mcp_server/mcp_protocol_server.py"],
                "env": {
                    "TABTABTAB_API_KEY": "your_api_key_here",
                    "TABTABTAB_SERVER_URL": "http://localhost:8000"
                }
            }
        }
    }
"""

import asyncio
import json
import os
import sys
import logging
from typing import Any, Optional, Sequence
import httpx

# Set up logging to file so we can see errors
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/tmp/mcp_server.log"),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger(__name__)

logger.info("Starting MCP server...")

# Try to import mcp, provide helpful error if not installed
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent

    logger.info("MCP imports successful")
except ImportError as e:
    logger.error(f"Failed to import MCP: {e}")
    print(
        "Error: MCP package not installed. Install it with: pip install mcp",
        file=sys.stderr,
    )
    sys.exit(1)

# Configuration from environment
TABTABTAB_API_KEY = os.getenv("TABTABTAB_API_KEY", "")
TABTABTAB_SERVER_URL = os.getenv("TABTABTAB_SERVER_URL", "http://localhost:8000")

logger.info(f"TABTABTAB_API_KEY set: {bool(TABTABTAB_API_KEY)}")
logger.info(f"TABTABTAB_SERVER_URL: {TABTABTAB_SERVER_URL}")

# Create MCP server instance
try:
    server = Server("google-sheets-mcp")
    logger.info("MCP server instance created")
except Exception as e:
    logger.error(f"Failed to create server: {e}", exc_info=True)
    raise


@server.list_tools()
async def handle_list_tools() -> Sequence[Tool]:
    """List available tools for the MCP client"""
    logger.info("handle_list_tools called")
    tools = [
        Tool(
            name="edit_google_sheet",
            description=(
                "Edit a Google Sheet using an AI agent. The agent can read, write, search, "
                "and manipulate Google Sheets data. Supports conversation history for follow-up edits. "
                "Returns streaming progress updates and final results."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The instruction for editing the sheet (e.g., 'Add a new row with Name: John, Email: john@example.com')",
                    },
                    "google_access_token": {
                        "type": "string",
                        "description": "Google OAuth 2.0 access token with Google Sheets API access",
                    },
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets spreadsheet ID (from the URL: docs.google.com/spreadsheets/d/{spreadsheet_id}/edit)",
                    },
                    "conversation_id": {
                        "type": "string",
                        "description": "Optional: Conversation ID to continue an existing conversation with context from previous edits",
                    },
                },
                "required": ["prompt", "google_access_token", "spreadsheet_id"],
            },
        ),
    ]
    logger.info(f"Returning {len(tools)} tools")
    return tools


async def stream_http_request(
    prompt: str,
    google_access_token: str,
    spreadsheet_id: str,
    conversation_id: Optional[str] = None,
) -> str:
    """Make HTTP request to our API and collect streaming responses"""

    if not TABTABTAB_API_KEY:
        return "Error: TABTABTAB_API_KEY environment variable not set. Please configure it in your MCP settings."

    url = f"{TABTABTAB_SERVER_URL}/mcp/edit_google_sheet"
    headers = {
        "X-API-Key": TABTABTAB_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "prompt": prompt,
        "google_access_token": google_access_token,
        "spreadsheet_id": spreadsheet_id,
    }

    if conversation_id:
        payload["conversation_id"] = conversation_id

    progress_messages = []
    tool_call_messages = []
    final_response = None
    error_message = None

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST", url, json=payload, headers=headers
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    return f"Error: HTTP {response.status_code} - {error_text.decode('utf-8')}"

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        try:
                            event = json.loads(data_str)
                            event_type = event.get("type")

                            if event_type == "progress":
                                message = event.get("message", "")
                                progress_messages.append(f"🔄 {message}")

                            elif event_type == "tool_call":
                                message = event.get("message", "")
                                tool_call_messages.append(f"🔧 {message}")

                            elif event_type == "response":
                                final_response = event

                            elif event_type == "error":
                                error_message = event.get("message", "Unknown error")

                        except json.JSONDecodeError:
                            continue

        # Build the response
        result_parts = []

        # Add tool calls section if any
        if tool_call_messages:
            result_parts.append("Tool Calls:")
            result_parts.extend(tool_call_messages)  # Show all tool calls
            result_parts.append("")

        # Add progress summary if any
        if progress_messages:
            result_parts.append("Progress:")
            result_parts.extend(
                progress_messages[-10:]
            )  # Limit to last 10 progress messages
            if len(progress_messages) > 10:
                result_parts.append(
                    f"... ({len(progress_messages) - 10} earlier progress updates)"
                )
            result_parts.append("")

        # Add final result or error
        if final_response:
            result_parts.append("✅ Success!")
            result_parts.append(f"Message: {final_response.get('message', '')}")
            conversation_id = final_response.get("conversation_id")
            if conversation_id:
                result_parts.append(f"Conversation ID: {conversation_id}")
                result_parts.append(
                    "(Use this conversation_id in follow-up requests to continue the conversation)"
                )
            turn_count = final_response.get("turn_count", 0)
            if turn_count:
                result_parts.append(f"Completed in {turn_count} turns")
            if final_response.get("partial"):
                result_parts.append("⚠️ Response is partial (reached turn limit)")

        elif error_message:
            result_parts.append(f"❌ Error: {error_message}")

        else:
            result_parts.append("⚠️ No response received from server")

        return "\n".join(result_parts)

    except httpx.TimeoutException:
        return "Error: Request timed out after 5 minutes. The task may still be processing."

    except Exception as e:
        return f"Error: {str(e)}"


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> Sequence[TextContent]:
    """Handle tool calls from the MCP client"""
    logger.info(f"handle_call_tool called with name={name}")

    if name != "edit_google_sheet":
        logger.error(f"Unknown tool requested: {name}")
        raise ValueError(f"Unknown tool: {name}")

    # Extract arguments
    prompt = arguments.get("prompt")
    google_access_token = arguments.get("google_access_token")
    spreadsheet_id = arguments.get("spreadsheet_id")
    conversation_id = arguments.get("conversation_id")

    # Validate required arguments
    if not prompt:
        return [TextContent(type="text", text="Error: 'prompt' is required")]

    if not google_access_token:
        return [
            TextContent(type="text", text="Error: 'google_access_token' is required")
        ]

    if not spreadsheet_id:
        return [TextContent(type="text", text="Error: 'spreadsheet_id' is required")]

    # Make the HTTP request and get the result
    result = await stream_http_request(
        prompt=prompt,
        google_access_token=google_access_token,
        spreadsheet_id=spreadsheet_id,
        conversation_id=conversation_id,
    )

    return [TextContent(type="text", text=result)]


async def main():
    """Main entry point for the MCP server"""
    logger.info("Entering main()")

    # Verify configuration
    if not TABTABTAB_API_KEY:
        logger.warning("TABTABTAB_API_KEY not set")
        print(
            "Warning: TABTABTAB_API_KEY environment variable not set. "
            "The server will start but tool calls will fail. "
            "Set it in your MCP configuration.",
            file=sys.stderr,
        )

    try:
        logger.info("Starting stdio server...")
        # Run the server using stdio transport
        async with stdio_server() as (read_stream, write_stream):
            logger.info("stdio server started, running MCP server...")
            await server.run(
                read_stream, write_stream, server.create_initialization_options()
            )
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        logger.info("__main__ starting")
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
