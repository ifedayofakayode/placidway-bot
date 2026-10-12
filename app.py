import re

import streamlit as st

import config
import ingest
import storage
from bot import Bot

MAX_QUESTIONS_PER_SESSION = 30      # protects your API quota on a public URL

st.set_page_config(page_title="PlacidWay Assistant", page_icon="💬")
st.title("💬 PlacidWay Assistant")
st.caption("Ask about treatments, costs and clinics. Answers come only from the PlacidWay pages shown as sources.")


@st.cache_resource
def get_bot():
    return Bot()


bot = get_bot()
ss = st.session_state
ss.setdefault("messages", [])
ss.setdefault("disclaimer_shown", False)
ss.setdefault("show_lead_form", False)
ss.setdefault("count", 0)
ss.setdefault("last_question", "")


def render(m):
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("sources"):
            st.caption("Sources: " + " · ".join(f"[{u}]({u})" for u in m["sources"]))


for m in ss.messages:
    render(m)

if q := st.chat_input("e.g. What is included in the package?"):
    if ss.count >= MAX_QUESTIONS_PER_SESSION:
        st.warning("Session limit reached. Please refresh the page to start a new chat.")
        st.stop()
    ss.count += 1
    history = [{"role": m["role"], "content": m["content"]} for m in ss.messages]
    with st.spinner("Searching the PlacidWay pages..."):
        r = bot.ask(q, history)

    text = r["answer"]
    if r["show_disclaimer"] and not ss.disclaimer_shown:      # show once per chat
        text += "\n\n" + config.DISCLAIMER
        ss.disclaimer_shown = True

    ss.messages += [{"role": "user", "content": q},
                    {"role": "assistant", "content": text, "sources": r["sources"]}]
    if r["category"] in ("not_in_content", "out_of_scope", "booking_request"):
        storage.log_unanswered(q, r["category"], r["top_score"])
    ss.show_lead_form = r["offer_quote"]
    ss.last_question = r["standalone_question"]
    st.rerun()

if ss.show_lead_form:
    with st.form("lead"):
        st.write("Would you like a free quote? Leave your details and the PlacidWay team can follow up.")
        name = st.text_input("Name")
        email = st.text_input("Email")
        st.caption("By submitting, you agree to be contacted about your quote request.")
        if st.form_submit_button("Request quote"):
            if name.strip() and re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()):
                storage.save_lead(name.strip(), email.strip(), ss.last_question)
                ss.show_lead_form = False
                st.success("Thank you! Your request has been recorded.")
            else:
                st.error("Please enter a name and a valid email.")

with st.sidebar:
    st.caption(f"Content last updated: {bot.retriever.built_at}")
    with st.expander("Admin"):
        pw = st.text_input("Password", type="password")
        if st.button("Refresh content"):
            if config.ADMIN_PASSWORD and pw == config.ADMIN_PASSWORD:
                with st.spinner("Re-reading the pages (about 10 seconds)..."):
                    summary = ingest.build_index()
                get_bot.clear()
                st.success(f"Refreshed: {summary['chunks']} chunks.")
            else:
                st.error("Wrong password.")