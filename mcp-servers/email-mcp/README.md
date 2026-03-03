# Email MCP Server

Python MCP server that exposes email tools to Claude Code via the Model Context Protocol.

## Tools

| Tool | Description |
|------|-------------|
| `send_email` | Send an email via Gmail SMTP (requires human approval first) |
| `draft_email` | Log a draft email without sending |
| `check_connection` | Verify SMTP connectivity |

## Setup

### 1. Install dependencies

```bash
pip install mcp python-dotenv
```

### 2. Configure .env

Copy `.env.example` to `.env` in the vault root and fill in:
```
GMAIL_SMTP_USER=your.email@gmail.com
GMAIL_SMTP_PASSWORD=your-app-password
GMAIL_FROM_NAME=AI Employee
```

### 3. Gmail App Password

This server uses Gmail SMTP with an App Password (not your account password).

1. Enable 2-Factor Authentication on your Google account
2. Go to: https://myaccount.google.com/apppasswords
3. Select "Mail" and your device
4. Copy the 16-character password → put in `GMAIL_SMTP_PASSWORD`

### 4. Register with Claude Code

The server is already registered in `.claude/settings.json`.
Claude Code loads it automatically when you open the vault.

To verify: run `claude mcp list` in the vault directory.

## Security

- All sends are blocked by default when `DRY_RUN=true` (safe default)
- The server logs every action to `/Logs/{date}.json`
- Never call `send_email` without verifying human approval in `/Approved/`

## Testing

```bash
# Test dry-run mode (safe)
DRY_RUN=true python server.py

# Test connection (requires real credentials)
DRY_RUN=false python server.py
# Then from Claude: use check_connection tool
```
