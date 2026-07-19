import json
import tempfile
import unittest
from pathlib import Path

from api.openai import _stream_content
from managers.session_manager import SessionManager


class StreamingTests(unittest.TestCase):
    def test_collects_split_sse_content_and_done_marker(self):
        first = b'data: {"choices":[{"delta":{"content":"hel"}}]}\n\n'
        second = b'data: {"choices":[{"delta":{"content":"lo"}}]}\n\ndata: [DONE]\n\n'
        buffer, content, done = _stream_content(first, b"")
        self.assertEqual(content, ["hel"])
        self.assertFalse(done)
        _, content, done = _stream_content(second, buffer)
        self.assertEqual(content, ["lo"])
        self.assertTrue(done)


class SessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_summary_survives_multiple_compactions(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = SessionManager(directory, max_recent_messages=2)
            await manager.save("example", [{"role": "user", "content": "first"}, {"role": "assistant", "content": "one"}, {"role": "user", "content": "second"}])
            context = await manager.context("example", [{"role": "user", "content": "third"}])
            self.assertIn("first", context[0]["content"])
            await manager.save("example", [{"role": "user", "content": "third"}, {"role": "assistant", "content": "three"}])
            saved = json.loads((Path(directory) / "example.json").read_text(encoding="utf-8"))
            self.assertIn("first", saved["summary"])


if __name__ == "__main__":
    unittest.main()
