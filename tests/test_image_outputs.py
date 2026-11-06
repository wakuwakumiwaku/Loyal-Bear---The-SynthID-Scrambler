"""Exercise the real image-save callback, replacing only the model boundary."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

from PIL import Image
import gradio

ROOT = Path(__file__).resolve().parents[1]


def load_gui():
    pipeline = types.ModuleType("src.pipeline")
    pipeline.load_pipeline = mock.Mock(side_effect=AssertionError("No model loading is permitted"))
    pipeline.run_img2img = mock.Mock()
    spec = importlib.util.spec_from_file_location("save_output_gui", ROOT / "src/gui.py")
    assert spec is not None and spec.loader is not None
    gui = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(ROOT))
    try:
        with mock.patch.dict(sys.modules, {"src.pipeline": pipeline}):
            spec.loader.exec_module(gui)
        from src import metadata
        assert Path(metadata.__file__).resolve() == ROOT / "src/metadata.py"
    finally:
        sys.path.pop(0)
    assert Path(gui.__file__).resolve() == ROOT / "src/gui.py"
    print("GUI_SOURCE", gui.__file__, "GRADIO", gradio.__version__, gradio.__file__)
    return gui, pipeline


class ImageOutputTests(unittest.TestCase):
    def test_two_callbacks_in_one_second_keep_both_images(self):
        gui, pipeline = load_gui()
        images = [Image.new("RGB", (2, 2), "red"), Image.new("RGB", (2, 2), "blue")]
        pipeline.run_img2img.side_effect = images
        gui.pipe = object()
        with tempfile.TemporaryDirectory() as directory, \
             mock.patch.object(gui, "OUTPUT_DIR", directory), \
             mock.patch("time.time", return_value=1700000000):
            gui.on_generate(images[0], "synthetic", "Light")
            first = next(Path(directory).glob("*.png"))
            first_bytes = first.read_bytes()
            result, status = gui.on_generate(images[1], "synthetic", "Strong")
            self.assertEqual(len(list(Path(directory).glob("*.png"))), 2,
                             "Every successful generation must preserve its own output, even in the same second")
            self.assertEqual(first.read_bytes(), first_bytes, "A later result must not overwrite an earlier image")
            self.assertEqual(result.getpixel((0, 0)), (0, 0, 255))
            self.assertIn(".png", status)
            colors = set()
            for path in Path(directory).glob("*.png"):
                with Image.open(path) as image:
                    colors.add(image.getpixel((0, 0)))
            self.assertEqual(colors, {(255, 0, 0), (0, 0, 255)})
        pipeline.load_pipeline.assert_not_called()

    def test_failed_save_does_not_leave_an_empty_output(self):
        gui, pipeline = load_gui()
        pipeline.run_img2img.return_value = Image.new("RGB", (1, 1), "green")
        gui.pipe = object()
        with tempfile.TemporaryDirectory() as directory, \
             mock.patch.object(gui, "OUTPUT_DIR", directory), \
             mock.patch.object(Image.Image, "save", side_effect=OSError("synthetic save failure")):
            with self.assertRaisesRegex(OSError, "synthetic save failure"):
                gui.on_generate(Image.new("RGB", (1, 1)), "synthetic", "Light")
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_missing_model_and_image_controls_do_not_generate(self):
        gui, pipeline = load_gui()
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(gui, "OUTPUT_DIR", directory):
            self.assertEqual(gui.on_generate(None, "", "Light"),
                             (None, "Model not loaded. Restart the app."))
            gui.pipe = object()
            self.assertEqual(gui.on_generate(None, "", "Light"),
                             (None, "Please provide an input image."))
            self.assertEqual(list(Path(directory).iterdir()), [])
        pipeline.run_img2img.assert_not_called()
        pipeline.load_pipeline.assert_not_called()


if __name__ == "__main__":
    unittest.main()
