"""
email-mcp/server.py — Email MCP Server for AI Employee (Silver Tier).

Exposes email tools to Claude Code via the Model Context Protocol (stdio).
Claude can call these tools to send and draft emails after human approval.

Tools exposed:
    send_email(to, subject, body, cc?, bcc?)  — Send via Gmail SMTP
    draft_email(to, subject, body)            — Log draft (DRY_RUN safe)
    check_connection()                        — Verify SMTP connectivity

Usage (stdio MCP — called by Claude Code via .mcp.json config):
    python server.py

Required environment variables:
    GMAIL_SMTP_USER       — Gmail sender address
    GMAIL_SMTP_PASSWORD   — Gmail App Password
    GMAIL_FROM_NAME       — Display name for outgoing emails (default: AI Employee)
    GMAIL_SMTP_HOST       — SMTP host (default: smtp.gmail.com)
    GMAIL_SMTP_PORT       — SMTP port (default: 587)

Register in Claude Code:
    Add to .claude/settings.json → mcpServers:
    {
      "email": {
        "command": "python",
        "args": ["<vault_path>/mcp-servers/email-mcp/server.py"],
        "env": {
          "GMAIL_SMTP_USER": "${GMAIL_SMTP_USER}",
          "GMAIL_SMTP_PASSWORD": "${GMAIL_SMTP_PASSWORD}"
        }
      }
    }

Dependencies:
    pip install mcp python-dotenv
"""

import asyncio
import json
import logging
import os
import smtplib
import ssl
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        CallToolResult,
        TextContent,
        Tool,
    )
except ImportError:
    print(
        "ERROR: mcp package not installed.\n"
        "Run: pip install mcp\n"
        "Then restart Claude Code.",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

SMTP_HOST = os.getenv("GMAIL_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("GMAIL_SMTP_PORT", "587"))
SMTP_USER = os.getenv("GMAIL_SMTP_USER", "")
SMTP_PASS = os.getenv("GMAIL_SMTP_PASSWORD", "")
FROM_NAME = os.getenv("GMAIL_FROM_NAME", "AI Employee")

# Vault path for logging
VAULT_PATH = Path(os.getenv("VAULT_PATH", Path(__file__).parent.parent.parent))
LOGS_DIR = VAULT_PATH / "Logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("email-mcp")


# ---------------------------------------------------------------------------
# SMTP helpers
# ---------------------------------------------------------------------------
def _build_message(
    to: str,
    subject: str,
    body: str,
    cc: str = "",
    bcc: str = "",
) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{FROM_NAME} <{SMTP_USER}>"
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    msg.attach(MIMEText(body, "plain", "utf-8"))
    return msg


def _send_via_smtp(
    to: str,
    subject: str,
    body: str,
    cc: str = "",
    bcc: str = "",
) -> dict:
    """Send an email via Gmail SMTP. Returns result dict."""
    if DRY_RUN:
        logger.info(f"[DRY RUN] Would send email to {to}: {subject}")
        return {
            "status": "dry_run",
            "to": to,
            "subject": subject,
            "timestamp": datetime.now().isoformat(),
        }

    if not SMTP_USER or not SMTP_PASS:
        return {
            "status": "error",
            "error": "GMAIL_SMTP_USER and GMAIL_SMTP_PASSWORD must be configured in .env",
        }

    try:
        msg = _build_message(to, subject, body, cc, bcc)
        recipients = [to] + ([cc] if cc else []) + ([bcc] if bcc else [])

        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, recipients, msg.as_string())

        logger.info(f"Email sent to {to}: {subject}")
        _log_action("email_sent", {"to": to, "subject": subject, "cc": cc})
        return {
            "status": "sent",
            "to": to,
            "subject": subject,
            "timestamp": datetime.now().isoformat(),
        }

    except smtplib.SMTPAuthenticationError:
        return {
            "status": "error",
            "error": "Authentication failed. Check GMAIL_SMTP_USER and GMAIL_SMTP_PASSWORD.",
        }
    except smtplib.SMTPException as e:
        _log_action("email_error", {"to": to, "subject": subject, "error": str(e)})
        return {"status": "error", "error": str(e)}


def _log_action(action_type: str, details: dict):
    """Append a structured log entry to /Logs/YYYY-MM-DD.json."""
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOGS_DIR / f"{today}.json"

    entry = {
        "timestamp": datetime.now().isoformat(),
        "action_type": action_type,
        "actor": "email_mcp",
        **details,
    }

    existing = []
    if log_file.exists():
        try:
            existing = json.loads(log_file.read_text(encoding="utf-8"))
        except Exception:
            existing = []

    existing.append(entry)
    log_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
server = Server("email-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="send_email",
            description=(
                "Send an email via Gmail SMTP. "
                "IMPORTANT: Only call this after verifying human approval exists "
                "in /Approved/ folder. Always confirm before sending."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient email address",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line",
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body (plain text)",
                    },
                    "cc": {
                        "type": "string",
                        "description": "CC recipient (optional)",
                        "default": "",
                    },
                    "bcc": {
                        "type": "string",
                        "description": "BCC recipient (optional)",
                        "default": "",
                    },
                },
                "required": ["to", "subject", "body"],
            },
        ),
        Tool(
            name="draft_email",
            description=(
                "Log an email draft to /Logs/ without sending. "
                "Use this to record what would be sent, then create an approval "
                "request in /Pending_Approval/ for human review."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body (plain text)"},
                },
                "required": ["to", "subject", "body"],
            },
        ),
        Tool(
            name="check_connection",
            description="Verify that the SMTP connection is configured and working.",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "send_email":
        result = _send_via_smtp(
            to=arguments["to"],
            subject=arguments["subject"],
            body=arguments["body"],
            cc=arguments.get("cc", ""),
            bcc=arguments.get("bcc", ""),
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "draft_email":
        draft = {
            "status": "drafted",
            "to": arguments["to"],
            "subject": arguments["subject"],
            "body_preview": arguments["body"][:200],
            "timestamp": datetime.now().isoformat(),
            "next_step": "Create approval request in /Pending_Approval/ for human review",
        }
        _log_action("email_drafted", {
            "to": arguments["to"],
            "subject": arguments["subject"],
        })
        return [TextContent(type="text", text=json.dumps(draft, indent=2))]

    elif name == "check_connection":
        if DRY_RUN:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "dry_run",
                    "configured": bool(SMTP_USER and SMTP_PASS),
                    "smtp_host": SMTP_HOST,
                    "smtp_port": SMTP_PORT,
                    "dry_run": True,
                }),
            )]
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
                s.ehlo()
                s.starttls(context=context)
                s.login(SMTP_USER, SMTP_PASS)
            return [TextContent(
                type="text",
                text=json.dumps({"status": "connected", "smtp_host": SMTP_HOST}),
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({"status": "error", "error": str(e)}),
            )]

    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
