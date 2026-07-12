"""
title: Zammad Draft
description: Create a shared draft answer for a Zammad ticket via the REST API so an agent can review and send it.
"""

import os
import uuid
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
        "Content-Type": "application/json",
    }


class Tools:
    def __init__(self):
        pass

    def create_zammad_draft(
        self,
        ticket_id: int = Field(
            ...,
            description="The numeric ID of the Zammad ticket to create the draft answer for.",
        ),
        body: str = Field(
            ...,
            description="The text of the draft answer. Plain text is converted to HTML line breaks.",
        ),
        subject: str = Field(
            "",
            description="Optional subject line for the draft answer.",
        ),
        article_type: str = Field(
            "email",
            description=(
                "Article type for the draft: 'email' for a customer reply (default) "
                "or 'note' for an internal note."
            ),
        ),
        to: str = Field(
            "",
            description="Optional recipient address for an email draft answer.",
        ),
        internal: bool = Field(
            False,
            description=(
                "Whether the drafted article is internal (agent-only). Defaults to "
                "false so the draft is a customer-facing reply."
            ),
        ),
    ) -> str:
        """
        Create a shared draft answer on a Zammad ticket. The draft is stored on the
        ticket so an agent can open it in the reply composer, review, and send it.
        """
        headers = _headers()
        if not headers:
            return "Error: no Zammad API token configured."

        text = (body or "").strip()
        if not text:
            return "Error: draft body must not be empty."

        html_body = text.replace("\n", "<br>\n")
        payload = {
            "form_id": uuid.uuid4().hex,
            "new_article": {
                "body": html_body,
                "content_type": "text/html",
                "type": article_type,
                "internal": bool(internal),
                "subject": subject,
                "to": to,
                "cc": "",
                "in_reply_to": "",
                "subtype": "",
                "ticket_id": int(ticket_id),
            },
            "ticket_attributes": {},
        }

        try:
            resp = requests.put(
                f"{ZAMMAD_URL}/api/v1/tickets/{ticket_id}/shared_draft",
                headers=headers,
                json=payload,
                timeout=15,
            )
        except requests.RequestException as e:
            return f"Error contacting Zammad: {e}"

        if resp.status_code in (401, 403):
            return f"Access denied for ticket: {ticket_id}"
        if resp.status_code == 404:
            return f"Ticket not found: {ticket_id}"
        if not resp.ok:
            return f"Error creating draft on ticket {ticket_id}: HTTP {resp.status_code}"

        data = resp.json()
        draft_id = data.get("shared_draft_id", "?")
        link = f"{ZAMMAD_URL}/#ticket/zoom/{ticket_id}"
        return (
            f"Shared draft answer created on ticket {ticket_id} "
            f"(draft ID {draft_id}, type {article_type}): {link}"
        )
