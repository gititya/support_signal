import os
import unittest

import anthropic


class AnthropicKeySmokeTest(unittest.TestCase):
    def test_anthropic_key_is_valid_when_present(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            self.skipTest("ANTHROPIC_API_KEY not set; skipping live API smoke test.")

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "hi"}],
        )
        self.assertTrue(response.content[0].text.strip())


if __name__ == "__main__":
    unittest.main()
