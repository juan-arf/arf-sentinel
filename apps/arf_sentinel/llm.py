import openai
from .config import settings

def get_nemotron_client():
    return openai.OpenAI(
        api_key=settings.NEBIUS_API_KEY,
        base_url=settings.NEBIUS_BASE_URL
    )

def generate_proposal(investigation_data: dict) -> dict:
    client = get_nemotron_client()
    messages = [
        {"role": "system", "content": "You are an enterprise software supply-chain investigator. Your job is to investigate evidence and propose remediation. You do not possess execution authority. Authorization is determined exclusively by ARF."},
        {"role": "user", "content": f"Based on this investigation: {investigation_data}, propose a remediation action."}
    ]
    response = client.chat.completions.create(
        model=settings.NEBIUS_MODEL,
        messages=messages,
        temperature=0.2,
        max_tokens=500
    )
    return {"proposal_text": response.choices[0].message.content}
