import json
import tempfile
import unittest
from pathlib import Path

from tools.image_tools import ImageGenerator

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


class ImageGeneratorTests(unittest.TestCase):
    def test_rejects_invalid_size_before_invoking_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            generator = ImageGenerator({"enabled": True, "output_directory": directory, "allowed_sizes": ["square"]})
            with self.assertRaisesRegex(ValueError, "WIDTHxHEIGHT"):
                generator.prepare("a test image", "square")

    def test_rejects_disabled_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            generator = ImageGenerator({"enabled": False, "output_directory": directory})
            with self.assertRaisesRegex(ValueError, "disabled"):
                generator.prepare("a test image", "1024x1024")

    def test_prepares_argument_list_and_cuda_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {name: root / name for name in ("sd-cli", "model.gguf", "vae.safetensors", "llm.gguf")}
            for path in paths.values():
                path.touch()
            generator = ImageGenerator({
                "enabled": True,
                "sd_cli": str(paths["sd-cli"]),
                "diffusion_model": str(paths["model.gguf"]),
                "vae": str(paths["vae.safetensors"]),
                "llm": str(paths["llm.gguf"]),
                "output_directory": str(root / "output"),
                "cuda_visible_devices": "0",
                "offload_to_cpu": True,
                "clip_on_cpu": True,
                "vae_on_cpu": True,
            })
            job = generator.prepare("a test image", "1024x1024")
            self.assertIn("a test image", job.command)
            self.assertEqual(job.environment["CUDA_VISIBLE_DEVICES"], "0")
            self.assertEqual(job.output_file.parent, root / "output")
            self.assertTrue({"--offload-to-cpu", "--clip-on-cpu", "--vae-on-cpu"}.issubset(job.command))

    def test_cpu_only_hides_cuda_devices(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {name: root / name for name in ("sd-cli", "model.gguf", "vae.safetensors", "llm.gguf")}
            for path in paths.values():
                path.touch()
            generator = ImageGenerator({
                "enabled": True,
                "sd_cli": str(paths["sd-cli"]),
                "diffusion_model": str(paths["model.gguf"]),
                "vae": str(paths["vae.safetensors"]),
                "llm": str(paths["llm.gguf"]),
                "output_directory": str(root / "output"),
                "cpu_only": True,
            })
            job = generator.prepare("a test image", "1024x1024")
            self.assertEqual(job.environment["CUDA_VISIBLE_DEVICES"], "")


if __name__ == "__main__":
    unittest.main()
