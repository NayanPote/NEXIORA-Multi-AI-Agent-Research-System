# Nexiora

**Next-generation intelligence** — a conversational AI assistant, powered by Mistral, that searches and reads the live web on its own when a question needs current or specific information.

Talk to Nexiora the way you'd talk to any chat assistant. When it decides a question needs up-to-date facts — recent news, prices, statistics, or anything it isn't fully confident about — it transparently runs web searches, reads the most relevant pages, and folds what it finds into its answer, with the source links shown right underneath. Full conversation memory is kept for the session, and a **Reset** button clears it and starts fresh.

---

## Features

- **Normal multi-turn conversation** — talks like a regular LLM chat assistant, not a rigid form-and-report tool.
- **Autonomous web research** — decides for itself when to call `web_search` (via Tavily) and `scrape_url`, runs multiple searches if needed, and cites the exact source URLs it used.
- **Conversation memory** — the full message history (including which tools were called) is preserved across turns in a session.
- **One-click reset** — clears the conversation and starts over, no page reload needed.
- **Single-page, dependency-light frontend** — plain HTML/CSS/JavaScript, no build step, no framework.
- **Stateless backend** — no database or server-side session; the client sends the conversation history back with every request.

---

## How it works

Each turn runs through a small tool-calling loop:

1. Your message, plus the full conversation history, is sent to the Mistral chat completions API along with two tool definitions: `web_search` and `scrape_url`.
2. Mistral decides whether it needs a tool. If the question is something it already knows confidently (general knowledge, explanations, math, writing help), it just answers.
3. If it needs current or specific information, it calls `web_search(query)` — this hits the Tavily search API and returns titles, URLs, and snippets. It can call this more than once with different phrasings.
4. If it needs more depth than a snippet gives, it calls `scrape_url(url)` to fetch and read the full text of a specific page.
5. Tool results are fed back to the model, which can call more tools or produce a final answer.
6. The final answer is returned to the browser along with the list of source URLs actually used, and appended to the conversation history for the next turn.

This talks directly to the Mistral API's native function/tool-calling — there's no LangChain agent layer in the loop, which keeps it simple, fast, and easy to debug.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask, Flask-CORS |
| LLM | Mistral (`mistralai` Python SDK), default model `mistral-small-latest` |
| Web search | Tavily API |
| Web scraping | `requests` + `BeautifulSoup` |
| Frontend | Plain HTML, CSS, JavaScript — no build tools, no frameworks |
| Production server | Gunicorn |

---

## Notes

- Conversation history lives entirely client-side and is sent with each request; there's no database or session store, so a page refresh or the **Reset** button simply clears it.
- Only the URLs a tool actually returned or fetched are shown as sources — nothing is inferred or guessed.

---

## Credits

Developed by **Nayan Pote**.
