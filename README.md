# eShipz Tracking MCP Server

A Model Context Protocol (MCP) server that provides shipment tracking functionality through the eShipz API. This server enables Claude Desktop to track packages across multiple carriers with intelligent, status-aware formatting.

## Features

- 📦 Track shipments across multiple carriers
- 🎯 Status-aware output formatting
- ✅ Automatic status detection (Delivered, In Transit, Exception, etc.)
- 🌍 Location-based updates
- 📊 Event count and timeline tracking
- 🔐 Secure API token management via environment variables

## Prerequisites

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- eShipz API token
- Claude Desktop app

## Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/mcp-eshipz.git
cd mcp-eshipz
```

2. Create a `.env` file in the project root:
```env
API_BASE_URL=https://app.eshipz.com
ESHIPZ_TOKEN=your_eshipz_api_token_here
```

3. Install dependencies:
```bash
uv sync
```

## Configuration

Add the server to your Claude Desktop configuration file:

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`  
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "eshipz_tracking": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\path\\to\\mcp-eshipz",
        "run",
        "main.py"
      ]
    }
  }
}
```

Replace `C:\\path\\to\\mcp-eshipz` with your actual project path.

## Usage

After configuring the server and restarting Claude Desktop, you can ask Claude to track packages:

- "Track package <your tracking id>"
- "What's the status of tracking number ABC123?"
- "Check delivery status for tracking XYZ789"

## Output Format

The server provides status-aware formatting:

- ✅ **Delivered**: Shows delivery date and location
- 🚚 **Out for Delivery**: Current facility location
- 📦 **In Transit**: Current location, latest update, and ETA
- ⚠️ **Exception**: Issue details and location
- 📭 **Picked Up**: Origin location
- ℹ️ **Info Received**: Shipment information received

Example output:
```
📦 In transit via DHL, currently in Mumbai - Shipment in transit
   Expected delivery: 2026-02-05
   Last updated: 2026-01-30 14:23:00
   Total events: 8
```

## Development

Run the server locally for testing:
```bash
uv run main.py
```

## Project Structure

```
mcp-eshipz/
├── main.py           # Main MCP server implementation
├── pyproject.toml    # Project dependencies
├── .env              # Environment variables (not in git)
├── .gitignore        # Git ignore rules
└── README.md         # This file
```

## Dependencies

- `httpx` - Async HTTP client
- `mcp` - Model Context Protocol SDK
- `python-dotenv` - Environment variable management

## Support

For issues or questions, please open an issue on GitHub.