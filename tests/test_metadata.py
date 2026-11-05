"""Metadata stripping preserves synthetic image pixels without model or GUI IO."""
import importlib.util
import io
from pathlib import Path
import unittest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("metadata", ROOT / "src/metadata.py")
assert SPEC is not None and SPEC.loader is not None
metadata = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(metadata)
assert Path(metadata.__file__).resolve() == ROOT / "src/metadata.py"


class StripMetadataTests(unittest.TestCase):
    def indexed_image(self):
        image = Image.new("P", (2, 1))
        image.putpalette([255, 0, 0, 0, 255, 0] + [0, 0, 0] * 254)
        image.putdata([0, 1])
        image.info["Comment"] = "remove synthetic metadata"
        image.getexif()[270] = "remove synthetic EXIF"
        return image

    def assert_clean_pixels(self, image):
        expected = image.convert("RGBA").tobytes()
        clean = metadata.strip_metadata(image)
        self.assertEqual(clean.convert("RGBA").tobytes(), expected, "Stripping metadata must not change displayed pixels")
        self.assertNotIn("Comment", clean.info)
        self.assertEqual(dict(clean.getexif()), {})
        stream = io.BytesIO()
        clean.save(stream, format="PNG")
        stream.seek(0)
        with Image.open(stream) as reloaded:
            self.assertEqual(reloaded.convert("RGBA").tobytes(), expected)
        self.assertEqual(image.info["Comment"], "remove synthetic metadata")
        return clean

    def test_palette_colors_survive_metadata_removal_and_png_save(self):
        image = self.indexed_image()
        clean = self.assert_clean_pixels(image)
        self.assertEqual(clean.mode, "P")
        self.assertIsNot(clean.palette, image.palette)
        clean.putpalette([0, 0, 0] * 256)
        self.assertEqual(image.convert("RGB").tobytes(), bytes([255, 0, 0, 0, 255, 0]))

    def test_rgba_palette_alpha_survives(self):
        image = self.indexed_image()
        image.putpalette([255, 0, 0, 0, 0, 255, 0, 128] + [0, 0, 0, 255] * 254, rawmode="RGBA")
        self.assert_clean_pixels(image)

    def test_indexed_transparency_survives(self):
        for transparency in (0, bytes([0, 128] + [255] * 254)):
            with self.subTest(transparency_type=type(transparency).__name__):
                image = self.indexed_image()
                image.info["transparency"] = transparency
                self.assert_clean_pixels(image)

    def test_rgb_transparency_is_rendering_data_not_descriptive_metadata(self):
        image = Image.new("RGB", (2, 1), (10, 20, 30))
        image.info.update(Comment="remove synthetic metadata", transparency=(10, 20, 30))
        self.assert_clean_pixels(image)

    def test_rgba_and_grayscale_controls(self):
        for mode, color in (("RGB", (1, 2, 3)), ("RGBA", (1, 2, 3, 40)), ("L", 123)):
            with self.subTest(mode=mode):
                image = Image.new(mode, (2, 1), color)
                image.info["Comment"] = "remove synthetic metadata"
                clean = self.assert_clean_pixels(image)
                self.assertEqual(clean.info, {})


if __name__ == "__main__":
    unittest.main()
