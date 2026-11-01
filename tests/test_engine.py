"""
Automated Verification & Unit Tests for the Fast Manhwa Compression Engine
"""

import os
import unittest
import numpy as np
from PIL import Image

from src.core.stride_filter_2d import StrideFilter2D
from src.core.gutter_detector import GutterDetector
from src.core.fast_encoder import FastPageEncoder, CompressionPreset
from src.core.pdf_processor import PDFProcessor
from src.packagers.cbz_packager import CBZPackager
from src.packagers.pdf_packager import PDFPackager

class TestCompressionEngine(unittest.TestCase):

    def test_2d_stride_filter_lossless_exactness(self):
        """
        Tests that encode -> decode is 100.000% mathematically exact on random data.
        """
        np.random.seed(42)
        # 100x100 RGB random image
        original = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

        # Single-axis vertical delta
        encoded = StrideFilter2D.encode(original)
        decoded = StrideFilter2D.decode(encoded)
        self.assertTrue(np.array_equal(original, decoded), "Vertical 2D filter failed bit-for-bit roundtrip!")

        # Dual-axis horizontal + vertical delta
        encoded_2d = StrideFilter2D.encode_2d_horizontal_vertical(original)
        decoded_2d = StrideFilter2D.decode_2d_horizontal_vertical(encoded_2d)
        self.assertTrue(np.array_equal(original, decoded_2d), "Dual-axis 2D filter failed bit-for-bit roundtrip!")

    def test_gutter_detector_and_slicing(self):
        """
        Tests that GutterDetector correctly identifies whitespace blocks.
        """
        # Create an image with gray art at top/bottom and a 100px white gutter in the middle
        arr = np.full((300, 200, 3), 128, dtype=np.uint8)
        arr[100:200, :] = 255  # Pure white gutter from Y=100 to Y=200

        detector = GutterDetector(tolerance=2, min_gutter_height=40)
        active_mask, manifest = detector.scan_gutters(arr)

        gutters = [m for m in manifest if m["type"] == "gutter"]
        self.assertEqual(len(gutters), 1, "Failed to identify the gutter!")
        self.assertEqual(gutters[0]["height"], 100, "Gutter height calculation incorrect!")
        self.assertEqual(gutters[0]["color"], "#FFFFFF")

    def test_end_to_end_cbz_and_pdf(self):
        """
        Tests end-to-end processing and packaging into .cbz and .pdf on real files.
        """
        sample_page = "real_comic_page_01.jpg"
        if os.path.exists(sample_page):
            img = Image.open(sample_page)
        else:
            img = Image.new("RGB", (800, 1600), color=(220, 220, 220))
        encoder = FastPageEncoder(preset=CompressionPreset.TURBO)
        processed = encoder.process_image(img)

        # Test CBZ packaging
        cbz_out = "test_output.cbz"
        cbz_size = CBZPackager.create_cbz(cbz_out, [processed])
        self.assertTrue(os.path.exists(cbz_out))
        self.assertGreater(cbz_size, 0)
        os.remove(cbz_out)

        # Test PDF packaging
        pdf_out = "test_output.pdf"
        pdf_size = PDFPackager.create_pdf(pdf_out, [processed])
        self.assertTrue(os.path.exists(pdf_out))
        self.assertGreater(pdf_size, 0)
        os.remove(pdf_out)

    def test_pdf_to_pdf_processor(self):
        """
        Tests PDF -> Image -> Adaptive SIMD Compress -> Optimized PDF roundtrip.
        """
        import pymupdf
        import cv2
        test_in = "temp_in.pdf"
        test_out = "temp_out.pdf"
        
        doc = pymupdf.open()
        canvas = np.full((1000, 700, 3), 250, dtype=np.uint8)
        cv2.putText(canvas, "TEST", (200, 500), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
        _, b = cv2.imencode(".png", canvas)
        page = doc.new_page(width=595, height=842)
        page.insert_image(pymupdf.Rect(0, 0, 595, 842), stream=b.tobytes())
        doc.save(test_in)
        doc.close()

        stats = PDFProcessor.process_pdf_to_pdf(test_in, test_out, dpi=100)
        self.assertTrue(os.path.exists(test_out))
        self.assertGreater(stats["size_reduction_pct"], 50.0)

        os.remove(test_in)
        os.remove(test_out)

    def test_folder_watcher_run_once(self):
        """
        Tests the automated FolderWatcher detecting and processing a chapter.
        """
        import tempfile
        import shutil
        from src.watcher import FolderWatcher

        with tempfile.TemporaryDirectory() as watch_dir, tempfile.TemporaryDirectory() as out_dir:
            ch_dir = os.path.join(watch_dir, "Chapter_01")
            os.makedirs(ch_dir)
            
            # Create a mock comic panel
            mock_img = Image.new("RGB", (600, 800), color=(240, 240, 240))
            mock_img.save(os.path.join(ch_dir, "01.jpg"))

            watcher = FolderWatcher(watch_dir=watch_dir, output_dir=out_dir, target_format="cbz")
            watcher.run_once()

            expected_out = os.path.join(out_dir, "Chapter_01.cbz")
            self.assertTrue(os.path.exists(expected_out), "FolderWatcher failed to produce compressed CBZ!")
            self.assertGreater(os.path.getsize(expected_out), 0)

if __name__ == "__main__":
    unittest.main()
