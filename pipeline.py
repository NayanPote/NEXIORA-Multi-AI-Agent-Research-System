import os
import json
import traceback

from dotenv import load_dotenv
from mistralai.client import Mistral

from tools import TOOL_SCHEMAS, TOOL_IMPLEMENTATIONS

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MODEL_NAME = os.getenv("MISTRAL_MODEL", "mistral-small-latest")

SYSTEM_PROMPT = (
    "You are Nexiora, a helpful, knowledgeable AI assistant developed by "
    "Nayan Pote in June 2026. If asked who created, built, developed, or made you, or "
    "who your developer/creator is, say you were developed by Nayan Pote "
    "— do not mention Mistral, Anthropic, or any other underlying provider "
    "in that context. Otherwise, have a normal conversation with the user. "
    "Answer directly and naturally, like a regular chat assistant, for "
    "things you already know well (definitions, explanations, general "
    "knowledge, math, writing help, etc).\n\n"
    "You have two tools: web_search(query) and scrape_url(url). You MUST "
    "use web_search before answering whenever the question involves any of "
    "the following, even if you think you already know the answer:\n"
    "- current events, news, or anything described as 'latest', 'recent', "
    "'current', 'today', 'now', or a specific year/date\n"
    "- prices, statistics, scores, rankings, or other figures that change "
    "over time\n"
    "- a request to 'research', 'find', 'look up', 'search for', or 'give "
    "me sources/links' on a topic\n"
    "- specific facts about a person, company, product, or event you are "
    "not fully certain about\n\n"
    "When researching a topic, don't stop at one search: run multiple "
    "web_search calls with different phrasings if needed, and use "
    "scrape_url on the most relevant result(s) to get real detail before "
    "answering. Never fabricate a URL or a fact - only state something as "
    "fact if it came from a tool result or something you are confident "
    "about. Always list the source URLs you actually used at the end of "
    "your answer when you used any tool. Keep answers clear and well "
    "organized; use short paragraphs or bullet points for research answers, "
    "and keep casual conversation replies concise."
)

MAX_TOOL_ROUNDS = 4  # safety cap on back-and-forth tool calls per turn


def _client() -> Mistral:
    if not MISTRAL_API_KEY:
        raise RuntimeError(
            "MISTRAL_API_KEY is not set. Add it to your .env file."
        )
    return Mistral(api_key=MISTRAL_API_KEY)


def _content_to_text(content) -> str:
    """
    Normalize Mistral message content into a plain string.

    The SDK can return content as a plain string, as None, or as a list of
    content-chunk objects (e.g. TextChunk) when the model streams mixed
    content. Only plain strings are JSON-serializable, so anything else
    must be flattened here before it goes into history or a JSON response.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for chunk in content:
            if isinstance(chunk, str):
                parts.append(chunk)
            elif isinstance(chunk, dict):
                parts.append(chunk.get("text", ""))
            else:
                parts.append(getattr(chunk, "text", "") or "")
        return "".join(parts)
    return str(content)


def _message_to_dict(msg) -> dict:
    """Normalize a Mistral SDK message object into a plain dict for history."""
    d = {"role": msg.role, "content": _content_to_text(msg.content)}
    if getattr(msg, "tool_calls", None):
        d["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in msg.tool_calls
        ]
    return d


def run_chat_turn(history: list) -> dict:
    """
    history: list of {"role": "user"|"assistant"|"system"|"tool", ...}
    representing the full conversation so far, ending with the newest
    user message.

    Returns {"reply": str, "history": updated_history, "sources": [urls]}
    """
    client = _client()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + list(history)
    sources_used = []

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.chat.complete(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.4,
        )

        choice = response.choices[0]
        msg = choice.message
        messages.append(_message_to_dict(msg))

        if not msg.tool_calls:
            # Final assistant answer - done.
            reply_text = _content_to_text(msg.content)
            return {
                "reply": reply_text,
                "history": messages[1:],  # drop the system prompt from stored history
                "sources": sources_used,
            }

        # Execute each requested tool call and feed results back.
        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            try:
                args = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            impl = TOOL_IMPLEMENTATIONS.get(fn_name)
            if impl is None:
                result = f"Unknown tool: {fn_name}"
            else:
                try:
                    result = impl(**args)
                except Exception as exc:
                    result = f"Tool '{fn_name}' failed: {exc}"

            if fn_name == "web_search":
                for line in str(result).splitlines():
                    if line.startswith("URL: "):
                        url = line[len("URL: "):].strip()
                        if url and url not in sources_used:
                            sources_used.append(url)
            elif fn_name == "scrape_url" and "url" in args:
                url = args["url"]
                if url not in sources_used:
                    sources_used.append(url)

            messages.append(
                {
                    "role": "tool",
                    "name": fn_name,
                    "tool_call_id": tool_call.id,
                    "content": str(result),
                }
            )

    # Ran out of tool rounds - ask for a direct final answer, no more tools.
    try:
        response = client.chat.complete(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.4,
        )
        reply_text = _content_to_text(response.choices[0].message.content) or (
            "I gathered some information but ran into trouble finishing my "
            "answer. Could you try rephrasing your question?"
        )
    except Exception:
        traceback.print_exc()
        reply_text = "Something went wrong while finishing my answer."

    messages.append({"role": "assistant", "content": reply_text})
    return {"reply": reply_text, "history": messages[1:], "sources": sources_used}