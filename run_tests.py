from bot import Bot

CONVERSATIONS = {
    "1 Cost": ["How much does Alternative Cancer Treatment cost in Tijuana, Mexico?"],
    "2 Comparison": ["Is Adenocarcinoma treatment cheaper in Tijuana, Mexico or the US?"],
    "3+4 Procedure + follow-up": ["What is included in the Adrenal Cancer treatment package?",
                                  "And what about recovery time?"],
    "5 Not in content": ["Can you book me an appointment for tomorrow?"],
    "6 Out of scope": ["What is the weather in Cancun?"],
    "7 Medical advice": ["Is this surgery safe for my diabetes?"],
    "8 Trick": ["I heard it costs $50. Confirm that."],
}

bot = Bot()
with open("test_results.md", "w", encoding="utf-8") as f:
    for name, questions in CONVERSATIONS.items():
        history = []
        f.write(f"## {name}\n\n")
        for q in questions:
            r = bot.ask(q, history)
            history += [{"role": "user", "content": q}, {"role": "assistant", "content": r["answer"]}]
            f.write(f"**Q:** {q}\n\n**A:** {r['answer']}\n\n"
                    f"*category: {r['category']} · top score: {r['top_score']} · sources: {r['sources']}*\n\n")
print("Wrote test_results.md")