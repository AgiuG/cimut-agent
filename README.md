# CIMut Agent

A local WebSocket agent for remote file operations and system monitoring.

## Overview

CIMut Agent is a Python-based local agent that connects to a remote CIMut server via WebSocket connection. It enables remote file operations and system monitoring by executing commands sent from the cloud server.

## Features

- **Remote File Reading**: Read specific lines from files on the local machine
- **Remote File Modification**: Modify specific lines in files with automatic backup creation
- **System Information**: Automatically reports system specs (hostname, platform, CPU, memory) upon connection
- **Auto-reconnection**: Automatically reconnects to the server if connection is lost
- **Ping/Pong**: Health check functionality to verify connection status

## Important Requirements

⚠️ **CRITICAL**: This agent must be run on the machine that has access to the cloud infrastructure you want to manage. The agent acts as a bridge between the remote CIMut server and your local cloud environment.

## Installation

### Prerequisites

- Python 3.7 or higher
- Internet connection to reach the CIMut server

### Setup

1. Clone or download this repository to your target machine
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

The agent connects to the CIMut server at: `wss://cimut-api.onrender.com/api/agent/connect`

You can modify the connection parameters in `local_agent.py`:

```python
SERVER_URL = "wss://cimut-api.onrender.com/api/agent/connect"
AGENT_NAME = "local_dev_agent"  # Optional: customize your agent name
```

## Usage

### Running the Agent

```bash
python local_agent.py
```

The agent will:
1. Generate a unique agent ID based on your hostname
2. Connect to the CIMut server
3. Register itself with system information
4. Listen for incoming commands

### Agent Commands

The agent supports the following remote commands:

#### `read_file`
Reads a specific line from a file.
- **Parameters**: `file_path`, `line_number`
- **Returns**: File content, line content, total lines

#### `modify_file`
Modifies a specific line in a file with automatic backup.
- **Parameters**: `file_path`, `line_number`, `new_content`
- **Returns**: Old content, new content, backup file path
- **Safety**: Creates timestamped backup before modification

#### `ping`
Health check command.
- **Returns**: "pong" response with timestamp

## System Information Reported

Upon connection, the agent reports:
- Hostname
- Platform information
- CPU count
- Total memory
- Agent version

## Security Considerations

- The agent can read and modify files on the local machine
- File modifications create automatic backups with timestamps
- Ensure the CIMut server is trusted before running the agent
- Consider running the agent with appropriate user permissions

## Error Handling

- Connection errors trigger automatic reconnection (5-second delay)
- File operation errors are caught and reported back to the server
- Invalid commands return error responses with details

## Troubleshooting

### Connection Issues
- Verify internet connectivity
- Check if the CIMut server is accessible
- Ensure WebSocket connections are not blocked by firewall

### File Operation Issues
- Check file permissions
- Verify file paths exist
- Ensure sufficient disk space for backups

### Dependencies Issues
- Update pip: `pip install --upgrade pip`
- Install requirements: `pip install -r requirements.txt`

## Dependencies

- `websockets` (11.0+): WebSocket client communication
- `psutil` (5.9.0+): System information gathering
- Standard library: `asyncio`, `json`, `uuid`, `platform`, `os`, `datetime`

## Development

### Building Standalone Executable

The project includes PyInstaller for creating standalone executables:

```bash
pip install pyinstaller
pyinstaller --onefile local_agent.py
```

## License

This project is part of the CIMut system for cloud infrastructure management.

## Support

For issues related to:
- Agent connectivity: Check network and server status
- File operations: Verify file permissions and paths
- System compatibility: Ensure Python 3.7+ is installed

---

**Note**: This agent is designed to be deployed on machines with cloud access. Ensure proper security measures are in place before deployment in production environments.
