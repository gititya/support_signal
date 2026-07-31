import os
import unittest

import openai


class OpenRouterKeySmokeTest(unittest.TestCase):
    def test_openrouter_key_is_valid_when_present(self):
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            self.skipTest("OPENROUTER_API_KEY not set; skipping live API smoke test.")

        client = openai.OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        response = client.chat.completions.create(
            model="anthropic/claude-haiku-4.5",
            max_tokens=10,
            messages=[{"role": "user", "content": "hi"}],
        )
        self.assertTrue(response.choices[0].message.content.strip())


if __name__ == "__main__":
    unittest.main()
