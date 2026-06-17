"""
title: Zammad Search
description: Search tickets in a Zammad instance via the REST API and return matching ticket summaries.
"""

import os
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


class Tools:
    def __init__(self):
        pass

    def search_zammad_tickets(
        self,
        query: str = Field(
            ...,
            description=(
                "Search query for Zammad tickets. Supports full-text and "
                "field-specific queries like 'state.name:open' or 'title:network'."
            ),
        ),
        limit: int = Field(
            10,
            description="Maximum number of tickets to return (default 10, max 100).",
        ),
    ) -> str:
        """
        Search the configured Zammad for the given query and return a list of
        matching tickets with their key metadata.
        """
        headers = _headers()
        if not headers:
            return "Error: no Zammad API token configured."

        limit = max(1, min(int(limit), 100))
        url = f"{ZAMMAD_URL}/api/v1/tickets/search"
        params = {"query": query, "limit": limit, "expand": "true"}

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)
        except requests.RequestException as e:
            return f"Error contacting Zammad: {e}"

        if resp.status_code in (401, 403):
            return "Access denied: check the Zammad API token."
        if not resp.ok:
            return f"Error searching Zammad: HTTP {resp.status_code}"

        data = resp.json()
        tickets = data if isinstance(data, list) else data.get("tickets") or []
        if not tickets:
            return f"No tickets found for: {query}"

        lines = [f"Found {len(tickets)} ticket(s) for '{query}':", ""]
        for t in tickets:
            tid = t.get("id")
            number = t.get("number", "?")
            title = t.get("title") or "(no title)"
            state = t.get("state", "?")
            priority = t.get("priority", "?")
            group = t.get("group", "?")
            owner = t.get("owner", "?")
            customer = t.get("customer", "?")
            updated = t.get("updated_at", "?")
            link = f"{ZAMMAD_URL}/#ticket/zoom/{tid}"
            lines.append(f"- #{number} (ID {tid}) — {title}: {link}")
            lines.append(
                f"  state: {state} | priority: {priority} | group: {group}"
            )
            lines.append(
                f"  owner: {owner} | customer: {customer} | updated: {updated}"
            )
        return "\n".join(lines)
