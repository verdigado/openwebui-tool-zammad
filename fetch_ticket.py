"""
title: Zammad Fetch
description: Fetch a Zammad ticket by ID including metadata and articles (messages/notes) via the REST API.
"""

import html
import os
import re
import requests
from pydantic import Field

ZAMMAD_URL = "https://zammad.example.com"
ZAMMAD_API_KEY = ""


def _headers() -> dict:
    token = ZAMMAD_API_KEY or os.getenv("ZAMMAD_API_KEY")
    if not token:
        return {}
    return {
        "Authorization": f"Token token={token}",
        "Accept": "application/json",
    }


def _html_to_text(content_html: str) -> str:
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", content_html, flags=re.S | re.I)
    s = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r"[\2](\1)", s, flags=re.S | re.I)
    s = re.sub(r"<li[^>]*>", "- ", s, flags=re.I)
    s = re.sub(r"</li>", "\n", s, flags=re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</p>", "\n\n", s, flags=re.I)
    s = re.sub(r"</(div|ul|ol|tr|table|h[1-6])>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n[ \t]+", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


class Tools:
    def __init__(self):
        pass

    def fetch_zammad_ticket(
        self,
        ticket_id: int = Field(
            ...,
            description="The numeric ID of the Zammad ticket to fetch.",
        ),
        include_articles: bool = Field(
            True,
            description="Whether to include the ticket's articles (messages/notes).",
        ),
    ) -> str:
        """
        Fetch a Zammad ticket by ID and return its metadata together with the
        ticket's articles converted to Markdown-like plain text.
        """
        headers = _headers()
        if not headers:
            return "Error: no Zammad API token configured."

        try:
            resp = requests.get(
                f"{ZAMMAD_URL}/api/v1/tickets/{ticket_id}",
                headers=headers,
                params={"expand": "true"},
                timeout=15,
            )
        except requests.RequestException as e:
            return f"Error contacting Zammad: {e}"

        if resp.status_code == 404:
            return f"Ticket not found: {ticket_id}"
        if resp.status_code in (401, 403):
            return f"Access denied for ticket: {ticket_id}"
        if not resp.ok:
            return f"Error fetching ticket {ticket_id}: HTTP {resp.status_code}"

        t = resp.json()
        link = f"{ZAMMAD_URL}/#ticket/zoom/{t.get('id')}"
        lines = [
            f"# Ticket #{t.get('number', '?')}: {t.get('title') or '(no title)'}",
            f"Source: {link}",
            f"State: {t.get('state', '?')}",
            f"Priority: {t.get('priority', '?')}",
            f"Group: {t.get('group', '?')}",
            f"Owner: {t.get('owner', '?')}",
            f"Customer: {t.get('customer', '?')}",
            f"Organization: {t.get('organization', '?')}",
            f"Created: {t.get('created_at', '?')}",
            f"Updated: {t.get('updated_at', '?')}",
        ]

        if not include_articles:
            return "\n".join(lines)

        try:
            ar = requests.get(
                f"{ZAMMAD_URL}/api/v1/ticket_articles/by_ticket/{ticket_id}",
                headers=headers,
                params={"expand": "true"},
                timeout=15,
            )
        except requests.RequestException as e:
            lines.append("")
            lines.append(f"Error fetching articles: {e}")
            return "\n".join(lines)

        if not ar.ok:
            lines.append("")
            lines.append(f"Error fetching articles: HTTP {ar.status_code}")
            return "\n".join(lines)

        articles = ar.json() or []
        lines.append("")
        lines.append(f"## Articles ({len(articles)})")
        for a in articles:
            sender = a.get("sender", "?")
            atype = a.get("type", "?")
            frm = a.get("from") or "?"
            to = a.get("to") or ""
            created = a.get("created_at", "?")
            internal = a.get("internal", False)
            subject = a.get("subject") or ""
            body = a.get("body") or ""
            if (a.get("content_type") or "").lower().startswith("text/html"):
                body = _html_to_text(body)
            else:
                body = body.strip()

            lines.append("")
            header = f"### [{created}] {sender}/{atype}"
            if internal:
                header += " (internal)"
            lines.append(header)
            lines.append(f"From: {frm}")
            if to:
                lines.append(f"To: {to}")
            if subject:
                lines.append(f"Subject: {subject}")
            lines.append("")
            lines.append(body)

        return "\n".join(lines)
