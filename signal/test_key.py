import anthropic, os

c = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
r = c.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=10,
    messages=[{"role": "user", "content": "hi"}],
)
print("Key valid:", r.content[0].text)
