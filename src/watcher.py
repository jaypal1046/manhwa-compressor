"""
Module: Automated Background Folder Watcher
Monitors a folder for incoming manhwa chapters (folders, .zip, .cbz, .pdf)
and automatically compresses them using the Adaptive SIMD Engine.
Ideal for Komga, Kavita, Suwayomi, and Scanlation automated drop-boxes.
"""

import os
import sys
import time
import shutil
import zipfile
import tempfile
from typing import Optional, Callable, Set

try:
    from .core.fast_encoder import FastPageEncoder, CompressionPreset
    from .core.pdf_processor import PDFProcessor
    from .packagers.cbz_packager import CBZPackager
    from .packagers.pdf_packager import PDFPackager
except ImportError:
    from src.core.fast_encoder import FastPageEncoder, CompressionPreset
    from src.core.pdf_processor import PDFProcessor
    from src.packagers.cbz_packager import CBZPackager
    from src.packagers.pdf_packager import PDFPackager


class FolderWatcher:
    """
    Watches an input directory for new chapter folders or archives (.zip, .cbz, .pdf).
    Automatically compresses and outputs clean CBZ or PDF files to the destination.
    """

    def __init__(
        self,
        watch_dir: str,
        output_dir: str,
        encoder: Optional[FastPageEncoder] = None,
        poll_interval: float = 2.0,
        delete_original: bool = False,
        target_format: str = "cbz"
    ):
        self.watch_dir = os.path.abspath(watch_dir)
        self.output_dir = os.path.abspath(output_dir)
        self.encoder = encoder or FastPageEncoder(preset=CompressionPreset.SIMD_ADAPTIVE)
        self.poll_interval = poll_interval
        self.delete_original = delete_original
        self.target_format = target_format.lower().lstrip(".")
        self.processed_files: Set[str] = set()

        os.makedirs(self.watch_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def is_file_ready(self, file_path: str, wait_seconds: float = 1.0) -> bool:
        """
        Ensures a file has finished copying/downloading before compression.
        Checks that file size remains stable and positive.
        """
        try:
            sz1 = os.path.getsize(file_path)
            time.sleep(wait_seconds)
            sz2 = os.path.getsize(file_path)
            return sz1 == sz2 and sz1 > 0
        except OSError:
            return False

    def process_chapter_dir(self, chapter_path: str) -> Optional[str]:
        """
        Compresses a folder of images into a single CBZ or PDF.
        """
        folder_name = os.path.basename(os.path.normpath(chapter_path))
        out_file = os.path.join(self.output_dir, f"{folder_name}.{self.target_format}")

        image_files = []
        for root, _, files in os.walk(chapter_path):
            for f in sorted(files):
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp')):
                    image_files.append(os.path.join(root, f))

        if not image_files:
            return None

        print(f"[{time.strftime('%X')}] [WATCHER] Detected chapter folder: '{folder_name}' ({len(image_files)} images)")
        t0 = time.time()

        processed_pages = []
        for img_path in image_files:
            res = self.encoder.process_file_path(img_path)
            if res:
                processed_pages.append(res)

        if not processed_pages:
            return None

        if self.target_format == "pdf":
            PDFPackager.create_pdf(out_file, processed_pages)
        else:
            CBZPackager.create_cbz(out_file, processed_pages)

        elapsed = time.time() - t0
        orig_sz = sum(os.path.getsize(f) for f in image_files)
        out_sz = os.path.getsize(out_file)
        cut_pct = (1.0 - out_sz / max(orig_sz, 1)) * 100

        print(f"[{time.strftime('%X')}] [WATCHER] Finished '{os.path.basename(out_file)}' in {elapsed:.2f}s! ({orig_sz/(1024*1024):.1f}MB -> {out_sz/(1024*1024):.1f}MB, Saved {cut_pct:.1f}%)")

        if self.delete_original:
            shutil.rmtree(chapter_path)

        return out_file

    def process_archive(self, archive_path: str) -> Optional[str]:
        """
        Compresses an existing .zip or .cbz archive into an optimized CBZ or PDF.
        """
        if not self.is_file_ready(archive_path):
            return None

        filename = os.path.basename(archive_path)
        base_name = os.path.splitext(filename)[0]
        out_file = os.path.join(self.output_dir, f"{base_name}.{self.target_format}")

        print(f"[{time.strftime('%X')}] [WATCHER] Detected archive: '{filename}'")
        t0 = time.time()

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    zf.extractall(temp_dir)
            except Exception as e:
                print(f"[{time.strftime('%X')}] [WATCHER Error] Failed to extract '{filename}': {e}", file=sys.stderr)
                return None

            image_files = []
            for root, _, files in os.walk(temp_dir):
                for f in sorted(files):
                    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp')):
                        image_files.append(os.path.join(root, f))

            if not image_files:
                return None

            processed_pages = [self.encoder.process_file_path(p) for p in image_files]
            processed_pages = [p for p in processed_pages if p is not None]

            if not processed_pages:
                return None

            if self.target_format == "pdf":
                PDFPackager.create_pdf(out_file, processed_pages)
            else:
                CBZPackager.create_cbz(out_file, processed_pages)

            elapsed = time.time() - t0
            orig_sz = os.path.getsize(archive_path)
            out_sz = os.path.getsize(out_file)
            cut_pct = (1.0 - out_sz / max(orig_sz, 1)) * 100

            print(f"[{time.strftime('%X')}] [WATCHER] Finished '{os.path.basename(out_file)}' in {elapsed:.2f}s! ({orig_sz/(1024*1024):.1f}MB -> {out_sz/(1024*1024):.1f}MB, Saved {cut_pct:.1f}%)")

            if self.delete_original:
                os.remove(archive_path)

            return out_file

    def process_pdf(self, pdf_path: str) -> Optional[str]:
        """
        Compresses an incoming PDF file into an optimized PDF or CBZ.
        """
        if not self.is_file_ready(pdf_path):
            return None

        filename = os.path.basename(pdf_path)
        base_name = os.path.splitext(filename)[0]
        out_file = os.path.join(self.output_dir, f"{base_name}.{self.target_format}")

        print(f"[{time.strftime('%X')}] [WATCHER] Detected PDF: '{filename}'")
        t0 = time.time()
        orig_sz = os.path.getsize(pdf_path)

        try:
            if self.target_format == "pdf":
                stats = PDFProcessor.process_pdf_to_pdf(pdf_path, out_file, encoder=self.encoder)
                out_sz = stats["compressed_size"]
                elapsed = stats["total_time"]
            else:
                pages = PDFProcessor.extract_pages_from_pdf(pdf_path)
                processed = [self.encoder.process_numpy_image(p) for p in pages]
                out_sz = CBZPackager.create_cbz(out_file, processed)
                elapsed = time.time() - t0

            cut_pct = (1.0 - out_sz / max(orig_sz, 1)) * 100
            print(f"[{time.strftime('%X')}] [WATCHER] Finished '{os.path.basename(out_file)}' in {elapsed:.2f}s! ({orig_sz/(1024*1024):.1f}MB -> {out_sz/(1024*1024):.1f}MB, Saved {cut_pct:.1f}%)")

            if self.delete_original:
                os.remove(pdf_path)

            return out_file
        except Exception as e:
            print(f"[{time.strftime('%X')}] [WATCHER Error] Failed to process PDF '{filename}': {e}", file=sys.stderr)
            return None

    def run_once(self):
        """
        Scans watch directory once and processes any new items.
        """
        try:
            entries = sorted(os.listdir(self.watch_dir))
        except OSError:
            return

        for item in entries:
            if item.startswith(('.', '_')):
                continue
            item_path = os.path.join(self.watch_dir, item)

            if item_path in self.processed_files:
                continue

            res = None
            if os.path.isdir(item_path):
                res = self.process_chapter_dir(item_path)
            elif item.lower().endswith(('.zip', '.cbz')):
                res = self.process_archive(item_path)
            elif item.lower().endswith('.pdf'):
                res = self.process_pdf(item_path)

            if res:
                self.processed_files.add(item_path)

    def start_watching(self, max_iterations: Optional[int] = None):
        """
        Starts the continuous monitoring loop.
        """
        print("=" * 68)
        print("      AUTOMATED SERVER WATCHER STARTED")
        print("=" * 68)
        print(f"Watching Folder   : {self.watch_dir}")
        print(f"Output Folder     : {self.output_dir}")
        print(f"Target Format     : .{self.target_format.upper()}")
        print(f"Polling Interval  : Every {self.poll_interval} seconds")
        print("Drop chapter folders, .cbz, .zip, or .pdf files into the watch folder!")
        print("Press Ctrl+C to stop.")
        print("-" * 68)

        iterations = 0
        try:
            while True:
                self.run_once()
                iterations += 1
                if max_iterations and iterations >= max_iterations:
                    break
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("\n[WATCHER] Stopped.")
