"""
Packager: Optimized PDF Builder
Assembles compressed page slices into a valid PDF document.
Handles proper aspect ratios and resolution scaling to prevent PDF engine errors.
"""

import os
from io import BytesIO
from typing import List, Dict, Any
from PIL import Image

try:
    import pymupdf
    from ..core.pdf_processor import PDFProcessor
    HAS_PYMUPDF = True
except Exception:
    try:
        import pymupdf
        from src.core.pdf_processor import PDFProcessor
        HAS_PYMUPDF = True
    except Exception:
        HAS_PYMUPDF = False

class PDFPackager:
    """
    Creates standards-compliant PDF documents from compressed comic slices.
    """

    @staticmethod
    def create_pdf(
        output_path: str,
        processed_pages: List[Dict[str, Any]]
    ) -> int:
        """
        Compiles all slices sequentially into an optimized PDF.
        Prefers PyMuPDF C-engine direct object injection when available.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # High-performance path: PyMuPDF direct stream insertion
        if HAS_PYMUPDF:
            all_slices = []
            for page in processed_pages:
                for s in page.get("slices", []):
                    all_slices.append(s)
            if all_slices:
                return PDFProcessor.create_optimized_pdf(output_path, all_slices)

        # Fallback path: Pillow standard PDF builder
        images: List[Image.Image] = []
        for page in processed_pages:
            for s in page.get("slices", []):
                img = Image.open(BytesIO(s["data"])).convert("RGB")
                images.append(img)

        if not images:
            raise ValueError("No images provided to create PDF")

        first_image = images[0]
        rest_images = images[1:]

        first_image.save(
            output_path,
            "PDF",
            resolution=150.0,
            save_all=True,
            append_images=rest_images
        )

        return os.path.getsize(output_path)
