# PlacidWay Website Knowledge Chatbot

A chatbot that answers visitor questions **only** from seven PlacidWay pages, cites the page each answer came from, and says "I don't know" (with a pointer to a free quote) when the answer is not in the content.

- Answers cost, package and clinic questions using the pages' own wording, including currency and context such as "starting from" or what a package includes.
- Refuses to invent prices, clinics or medical facts, and does not agree with wrong prices supplied by the user.
- Includes a simple chat UI, an admin refresh button, multilingual answers, follow-up handling, lead capture and an unanswered-question log.

**Live demo:** `https://placidway-bot.streamlit.app/`
**Repository:** `https://github.com/ifedayofakayode/placidway-bot`

---

## 1. Architecture

```
  ┌─────────┐   ┌─────────┐   ┌──────────┐   ┌─────────┐   ┌──────────┐
  │ INGEST  │──▶│  INDEX  │──▶│ RETRIEVE │──▶│   LLM   │──▶│  VERIFY  │──▶ Answer + sources
  │ ingest  │   │ index   │   │ retriever│   │ bot.py  │   │ bot.py   │
  │  .py    │   │ .json   │   │   .py    │   │ llm.py  │   │          │
  └─────────┘   └─────────┘   └──────────┘   └─────────┘   └──────────┘
   7 URLs        chunks +      top-5 chunks   strict rules,   sources real?
   cleaned       embeddings    above score    JSON output     numbers in
   & chunked                   threshold                      the context?
```

**Ingest (`ingest.py`).** The script fetches only the seven URLs listed in `config.py` (it never follows links). For each page it removes menus, scripts, footers and other noise, then keeps headings, paragraphs, list items and table rows. Table rows are kept together as `name | price | includes` so prices stay attached to what they belong to. The text is split into chunks of up to about 900 characters, each grouped under its nearest heading and prefixed with the page title. A readable dump is written to `data/chunks_preview.txt` so extraction quality can be inspected by eye.

**Index (`data/index.json`).** Each chunk is turned into an embedding (a list of numbers capturing its meaning) with a local model. The chunks, their source URLs and embeddings are saved in one JSON file together with a "built at" timestamp. With only seven pages, a JSON file plus NumPy is simpler, easier to explain and faster to deploy than a vector database. The file is committed to git, so the live app never needs to scrape.

**Retrieve (`retriever.py`).** On startup the index is loaded and normalised. For each question, the question is embedded, compared with every chunk by cosine similarity, and the top 5 chunks are returned with their scores. Chunks scoring below `MIN_SCORE` (set in `config.py`) are discarded.

**LLM (`bot.py`, `llm.py`).** Two model calls per message. The first rewrites the user's message into a standalone English question (resolving follow-ups such as "what about Turkey?") and detects its language. The second receives only the retrieved chunks, each labelled with its URL, plus strict rules: use only the context, quote prices exactly with their currency and context, never guess or convert, refuse medical advice, decline unrelated topics, and answer in the user's language. It returns JSON containing a category, the answer, the sources used, and disclaimer/quote flags. Temperature is 0 for consistency.

**Verify (`bot.py`).** The model's output is never trusted blindly. Code checks that every cited URL was actually in the retrieved context, and that every number in the answer appears in the retrieved text or in the user's own message. If an "answered" reply has no valid source or contains an unsupported number, it is replaced by the safe fallback message.

---

## 2. Tools and why

| Part | Choice | Why |
|---|---|---|
| Language | Python | Best libraries for scraping and AI, easy to read and explain |
| Scraping | `requests` + `BeautifulSoup` | Simple, and makes it easy to respect robots.txt and rate limits |
| Embeddings | `fastembed` (`BAAI/bge-small-en-v1.5`) | Free, runs locally, no PyTorch, light enough for free hosting |
| Vector store | JSON file + `numpy` | Only seven pages; a database would be overkill and harder to explain |
| LLM | Any OpenAI-compatible API (OpenAI, Gemini free tier, Groq free tier) | One code path; switch provider by changing three settings |
| UI + hosting | Streamlit + Streamlit Community Cloud | Built-in chat components, free public URL |
| Logs and leads | CSV file + optional Google Sheet webhook | Free, and the Sheet persists when the host restarts |

The model used in the live deployment is: `OpenAI gpt-4o-mini`.

---

## 3. Setup

Requires Python 3.11 or 3.12.

```bash
# 1. Clone
git clone https://github.com/ifedayofakayode/placidway-bot.git
cd placidway-bot

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows:    .venv\Scripts\activate
# Mac/Linux:  source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure secrets
cp .env.example .env          # Windows: copy .env.example .env
# then open .env and fill in your values

# 5. Build the knowledge base (fetches the 7 pages, writes data/index.json)
python ingest.py

# 6. Run the app
streamlit run app.py
```

### Environment variables (`.env`)

| Variable | Purpose |
|---|---|
| `LLM_API_KEY` | API key for your LLM provider |
| `LLM_BASE_URL` | Provider endpoint; leave blank for OpenAI |
| `LLM_MODEL` | Model name, e.g. `gpt-4o-mini` |
| `ADMIN_PASSWORD` | Password for the in-app refresh button |
| `SHEETS_WEBHOOK_URL` | Optional Google Apps Script URL for durable logs |
| `SHEETS_TOKEN` | Optional shared secret checked by that script |

No secrets are stored in the code. `.env` is git-ignored.

### Run the test questions

```bash
python run_tests.py     # writes test_results.md
```

---

## 4. Refreshing the content

There are two ways to update the bot when the PlacidWay pages change.

**Method 1: Admin button (immediate).** Open the app, expand **Admin** in the sidebar, enter the admin password and click **Refresh content**. The app re-reads the seven pages, rebuilds the index and reloads it. The sidebar shows when the content was last updated. On free hosting this refreshed index can be lost when the app restarts.

**Method 2: Re-ingest and commit (permanent).** Run this on your own computer:

```bash
python ingest.py
git add data/index.json
git commit -m "Refresh content"
git push
```

The hosting platform redeploys with the new index. This is the recommended way to make a refresh permanent.

---

## 5. Anti-hallucination design

A small, reliable bot matters more than an impressive one that makes things up, so the model is constrained by the prompt **and** by code.

1. **Score gate.** Only chunks whose similarity score is at least `MIN_SCORE` reach the LLM. For unrelated questions (such as the weather) nothing passes, so the model receives an empty context and has nothing to invent from.
2. **Source validation.** The model must list the URLs it used. Any URL that was not in the retrieved context is dropped. An "answered" reply with no valid source is downgraded to the "I don't know" fallback.
3. **Number check.** Every number with two or more digits in an answer must appear in the retrieved text or in the user's own message. Otherwise the answer is replaced by the fallback. This catches invented prices.
4. **Categories.** Each reply is classified as `answered`, `not_in_content`, `out_of_scope`, `medical_advice` or `booking_request`. The category drives behaviour: sources are shown only for answered and medical-advice replies, booking requests offer the quote form, and unanswerable categories are logged.
5. **Prompt rules.** The model is told never to guess, round, average or convert currencies, to compare treatments or countries only when both are in the content, to refuse diagnosis and medical judgements, to say so when a page lists no price, and to compare any price the user states against the page instead of agreeing with it.
6. **Safe failure.** If the LLM call fails or returns invalid JSON, the user gets the fallback message rather than an unchecked answer.

The number check is a safety net, not a guarantee. If a user states a wrong price and the model wrongly confirms it, the number passes the check because it appears in the user's message. That case is handled by the prompt rule on user-stated facts and is covered by test question 8.

---

## 6. Nice-to-haves implemented

- **Multilingual answers.** The user's language is detected, the question is translated to English for retrieval (the embedding model is English-first), and the answer is written in the user's language.
- **Follow-up questions.** The last six chat messages are used to rewrite "And what about recovery time?" into a complete standalone question before searching.
- **Medical disclaimer shown once.** A short disclaimer is added only when the answer touches health or treatment matters, and only the first time in a chat.
- **Lead capture.** When the user wants a quote or booking, or a price is not listed, the app shows a name and email form with basic email validation and a consent note. Leads are saved to `data/leads.csv` and, if configured, a Google Sheet.
- **Unanswered-question log.** Questions that were not answerable, out of scope or booking requests are logged with a timestamp, category and top retrieval score, so content gaps can be found. Saved to `data/unanswered.csv` and, if configured, a Google Sheet.
- **Cost protection.** A per-session question limit protects the API quota on a public URL.

---

## 7. Polite crawling

- **robots.txt is checked** before any page is fetched. Disallowed URLs are skipped and reported.
- **Clear User-Agent:** `PlacidWayAssessmentBot/1.0 (candidate assessment; contact: steven.fakayode@gmail.com)`.
- **Rate limit:** about one request per second (`REQUEST_DELAY = 1.0`).
- **No crawling beyond the seven URLs.** The script never follows links or paginates.

---

## Project structure

```
placidway-bot/
├── app.py            # chat UI, lead form, admin refresh
├── bot.py            # question rewriting, answering, guardrails
├── ingest.py         # fetch → clean → chunk → embed → save
├── retriever.py      # semantic search over the index
├── llm.py            # single function that calls the LLM
├── storage.py        # unanswered-question log and leads
├── config.py         # all settings in one place
├── run_tests.py      # runs the 8 test questions
├── data/index.json   # built knowledge base (committed)
├── requirements.txt
├── .env.example
└── README.md
```