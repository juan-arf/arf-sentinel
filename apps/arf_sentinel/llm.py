"""
Nebius / Nemotron LLM client.

Provides a thin wrapper around the OpenAI‑compatible API exposed by
Nebius Token Factory.  Used to generate structured remediation proposals
from the investigation evidence.

The system prompt explicitly instructs Nemotron that it **does not**
possess execution authority – that is exclusively ARF's domain.
"""

import openai
from .config import settings


def get_nemotron_client() -> openai.OpenAI:
    """
    Return an OpenAI client configured for the Nebius Token Factory.

    Uses the environment variables `NEBIUS_API_KEY` and `NEBIUS_BASE_URL`
    to authenticate and target the API.

    Returns
    -------
    openai.OpenAI
        A synchronous OpenAI‑compatible client.
    """
    return openai.OpenAI(
        api_key=settings.NEBIUS_API_KEY,
        base_url=settings.NEBIUS_BASE_URL,
    )


def generate_proposal(investigation_data: dict) -> dict:
    """
    Send investigation data to Nemotron and extract a remediation proposal.

    The model is instructed to investigate the evidence and propose a
    remediation action, but **never** to authorise it.  Authorisation is
    reserved for the ARF governance engine.

    Parameters
    ----------
    investigation_data : dict
        A dictionary containing the CRAFT evidence summary, dependency
        counts, and blast‑radius metrics.

    Returns
    -------
    dict
        A dictionary with the key `proposal_text` containing the raw
        LLM response.  In production, this would be parsed into a
        `RemediationProposal` object.
    """
    client = get_nemotron_client()
    messages = [
        {
            "role": "system",
            "content": (
                "You are an enterprise software supply‑chain investigator. "
                "Your job is to investigate evidence and propose remediation. "
                "You do not possess execution authority. "
                "Authorization is determined exclusively by ARF."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Based on this investigation: {investigation_data}, "
                f"propose a remediation action."
            ),
        },
    ]
    response = client.chat.completions.create(
        model=settings.NEBIUS_MODEL,
        messages=messages,
        temperature=0.2,
        max_tokens=500,
    )
    return {"proposal_text": response.choices[0].message.content}
