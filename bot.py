import re

import config
from llm import chat_json
from retriever import Retriever

CONDENSE_SYSTEM = """You prepare chat messages for a search engine.
Given the chat history and the user's latest message, return JSON:
{"standalone_question": "...", "language": "..."}
- standalone_question: the latest message rewritten IN ENGLISH as a complete question that
  makes sense without the history. Resolve references such as "there", "it", "what about Turkey?".
  Do NOT answer it.
- language: the language the latest message is written in (e.g. English, Spanish, Arabic)."""

ANSWER_SYSTEM = """You are the PlacidWay website assistant. PlacidWay is a medical tourism platform.
You receive CONTEXT passages taken from PlacidWay pages, each labelled with its source URL.

STRICT RULES
1. Use ONLY the CONTEXT for facts, prices, clinics, treatments and medical information.
   Never use outside knowledge. Never guess, estimate, round, average or convert currencies.
2. Prices: quote exactly as written, with the currency and all context the page gives
   (e.g. "starting from", what the package includes). If the page lists no price, say the
   price is not listed and suggest requesting a free quote from PlacidWay.
3. If the user states a fact (e.g. "I heard it costs $50, confirm"), compare it to the CONTEXT.
   Never confirm anything the CONTEXT does not support. Say what the page actually lists.
4. Comparisons between treatments or countries: only compare what the CONTEXT covers for BOTH.
   If one side is missing, say so.
5. Medical advice (safety for a condition, diagnosis, what they should do): do NOT judge or diagnose.
   Say you cannot give medical advice and recommend speaking to their doctor. You may mention
   general information the CONTEXT states.
6. Requests to book or schedule: you cannot book anything. Offer to collect their name and
   email for a free quote request, or point them to PlacidWay's contact/quote form.
7. Unrelated topics (weather, news, etc.): politely decline and say you can only help with
   questions about the PlacidWay pages.
8. If the CONTEXT does not contain the answer: say you don't have that information and
   suggest contacting PlacidWay for a free quote.
9. Write the answer in {language}. Be concise and clear.

Return JSON only:
{"category": "answered | not_in_content | out_of_scope | medical_advice | booking_request",
 "answer": "...",
 "sources": ["exact URLs from the CONTEXT that you used"],
 "show_disclaimer": true/false,   // true only if the answer touches treatment or health matters
 "offer_quote": true/false}       // true if the user wants a quote, booking or a price not listed"""

VALID = {"answered", "not_in_content", "out_of_scope", "medical_advice", "booking_request"}
NUM = re.compile(r"\d[\d,]*\.?\d*")


def numbers(text):
    """All numbers with 2+ digits in a text, normalised ('3,500' -> '3500')."""
    out = set()
    for m in NUM.findall(text):
        n = m.replace(",", "").rstrip(".")
        if len(n.replace(".", "")) >= 2:
            out.add(n)
    return out


def fmt_history(history):
    return "\n".join(f"{m['role']}: {m['content']}" for m in history[-6:]) or "(none)"


def fmt_context(hits):
    return "\n\n".join(f"[Source: {h['url']}]\n{h['text']}" for h in hits)


class Bot:
    def __init__(self):
        self.retriever = Retriever()

    def ask(self, question, history=()):
        # 1. Rewrite + detect language
        try:
            c = chat_json(CONDENSE_SYSTEM,
                          f"CHAT HISTORY:\n{fmt_history(list(history))}\n\nLATEST MESSAGE: {question}")
            standalone = c.get("standalone_question") or question
            language = c.get("language") or "English"
        except Exception:
            standalone, language = question, "the same language as the user's message"

        # 2. Retrieve, then gate on similarity score
        hits = self.retriever.search(standalone)
        good = [h for h in hits if h["score"] >= config.MIN_SCORE]
        context = fmt_context(good) if good else "(no relevant passages found)"

        # 3. Generate
        try:
            out = chat_json(
                ANSWER_SYSTEM.replace("{language}", language),
                f"CONTEXT:\n{context}\n\nQUESTION: {standalone}\n"
                f"USER'S ORIGINAL MESSAGE: {question}")
        except Exception:
            return self._result("not_in_content", config.FALLBACK, [], standalone, top=hits)

        # 4. Verify in code
        return self._verify(out, good, question, standalone, hits)

    def _verify(self, out, good, question, standalone, hits):
        category = out.get("category") if out.get("category") in VALID else "not_in_content"
        answer = (out.get("answer") or "").strip()
        allowed = {h["url"] for h in good}
        sources = [u for u in out.get("sources", []) if u in allowed]

        if category == "answered":
            context_nums = set().union(*[numbers(h["text"]) for h in good]) if good else set()
            invented = numbers(answer) - context_nums - numbers(question)
            if not answer or not sources or invented:      # uncited or unsupported → refuse
                category = "not_in_content"

        if category == "not_in_content" and not out.get("answer") or \
           (category == "not_in_content" and out.get("category") == "answered"):
            answer = config.FALLBACK
        if category not in ("answered", "medical_advice"):
            sources = []

        return self._result(category, answer, sources, standalone, hits,
                            disclaimer=bool(out.get("show_disclaimer")),
                            quote=bool(out.get("offer_quote")) or category == "booking_request")

    @staticmethod
    def _result(category, answer, sources, standalone, top, disclaimer=False, quote=False):
        return {"category": category, "answer": answer, "sources": sources,
                "standalone_question": standalone, "show_disclaimer": disclaimer,
                "offer_quote": quote,
                "top_score": round(top[0]["score"], 3) if top else 0}