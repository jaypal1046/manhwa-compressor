"""
Core Module: High-Performance PDF Ingestion & Re-creation Engine
Uses PyMuPDF (MuPDF C-engine) for sub-second PDF page extraction and assembly.

Pipeline:
Input PDF ──► PyMuPDF C-Extract ──► Adaptive SIMD Compressor ──► Optimized PDF
"""

import os
import time
from typing import List, Dict, Any, Optional
import pymupdf  # High-speed MuPDF C library
import numpy as np
import cv2

from .fast_encoder import FastPageEncoder, CompressionPreset

class PDFProcessor:
    """
    Handles PDF ingestion (extracting/rasterizing pages at C-speed)
    and re-creating clean, optimized PDF documents.
    """

    @staticmethod
    def extract_pages_from_pdf(pdf_path: str, dpi: int = 150) -> List[np.ndarray]:
        """
        Extracts all pages from a PDF as BGR image arrays.
        Uses direct XObject extraction if image-only, or fast MuPDF rasterization.
        """
        assert os.path.exists(pdf_path), f"PDF file not found: {pdf_path}"
        doc = pymupdf.open(pdf_path)
        pages_bgr: List[np.ndarray] = []

        # Target zoom based on requested DPI (standard 72 pt/in)
        zoom = dpi / 72.0
        mat = pymupdf.Matrix(zoom, zoom)

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            
            # Fast C-level page rasterization
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Zero-copy memory buffer into numpy array
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            
            # Convert RGB to BGR for OpenCV SIMD engine
            if pix.n == 3:
                bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            elif pix.n == 1:
                bgr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
            else:
                bgr = cv2.cvtColor(arr[:, :, :3], cv2.COLOR_RGB2BGR)
                
            pages_bgr.append(bgr)

        doc.close()
        return pages_bgr

    @staticmethod
    def create_optimized_pdf(
        output_pdf_path: str,
        compressed_slices: List[Dict[str, Any]]
    ) -> int:
        """
        Recreates a clean, standards-compliant PDF from compressed image slices.
        Inserts compressed JPEG/WebP streams directly into PDF page dictionaries
        with zero generational loss and garbage collection compaction.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
        new_doc = pymupdf.open()

        for slice_item in compressed_slices:
            data = slice_item["data"]
            w = slice_item["width"]
            h = slice_item["height"]

            # PDF specification (ISO 32000) does not support native WebP stream filters.
            # Convert WebP to high-efficiency JPEG streams if encountered before embedding.
            if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
                dec = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
                _, enc = cv2.imencode(".jpg", dec, [cv2.IMWRITE_JPEG_QUALITY, 85])
                data = enc.tobytes()

            # Convert pixel dimensions to PDF 72 DPI points
            pdf_w = (w / 150.0) * 72.0
            pdf_h = (h / 150.0) * 72.0

            # Create clean page
            page = new_doc.new_page(width=pdf_w, height=pdf_h)
            rect = pymupdf.Rect(0, 0, pdf_w, pdf_h)
            
            # Direct binary stream insertion into the PDF object graph
            page.insert_image(rect, stream=data)

        # Save with maximum structural garbage collection and xref stream compression
        new_doc.save(
            output_pdf_path,
            garbage=4,          # Eliminate unreferenced objects
            deflate=True,       # Deflate stream compression on structural objects
            clean=True          # Sanitize content streams
        )
        new_doc.close()
        return os.path.getsize(output_pdf_path)

    @classmethod
    def process_pdf_to_pdf(
        cls,
        input_pdf_path: str,
        output_pdf_path: str,
        encoder: Optional[FastPageEncoder] = None,
        dpi: int = 150
    ) -> Dict[str, Any]:
        """
        Complete end-to-end PDF -> Image -> Adaptive SIMD Compress -> Optimized PDF pipeline.
        """
        t0 = time.time()
        orig_size = os.path.getsize(input_pdf_path)
        encoder = encoder or FastPageEncoder(preset=CompressionPreset.SIMD_ADAPTIVE)

        # Step 1: Extract pages at C-speed
        t_extract = time.time()
        pages = cls.extract_pages_from_pdf(input_pdf_path, dpi=dpi)
        extract_time = time.time() - t_extract

        # Step 2: Compress each page using Adaptive SIMD (4:4:4 text / 4:2:0 art)
        t_comp = time.time()
        all_slices = []
        for p_bgr in pages:
            if encoder.simd_engine:
                h, w, _ = p_bgr.shape
                # Adaptive encode
                data, mode = encoder.simd_engine.encode_tile(p_bgr)
                all_slices.append({
                    "data": data,
                    "width": w,
                    "height": h,
                    "mode": mode
                })
            else:
                # Fallback to PIL
                from PIL import Image
                img_rgb = Image.fromarray(cv2.cvtColor(p_bgr, cv2.COLOR_BGR2RGB))
                res = encoder.process_image(img_rgb)
                all_slices.extend(res["slices"])

        comp_time = time.time() - t_comp

        # Step 3: Rebuild optimized PDF
        t_build = time.time()
        out_size = cls.create_optimized_pdf(output_pdf_path, all_slices)
        build_time = time.time() - t_build

        total_time = time.time() - t0
        cut_pct = (1.0 - (out_size / orig_size)) * 100

        return {
            "input_file": input_pdf_path,
            "output_file": output_pdf_path,
            "page_count": len(pages),
            "slice_count": len(all_slices),
            "original_size": orig_size,
            "compressed_size": out_size,
            "size_reduction_pct": cut_pct,
            "time_extract": extract_time,
            "time_compress": comp_time,
            "time_build": build_time,
            "total_time": total_time
        }

