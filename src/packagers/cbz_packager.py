"""
Packager: Standard CBZ (Comic Book Zip) Archive Builder
Packages compressed slices into an industry-standard .cbz file compatible
with all modern comic reader apps (Mihon, Tachiyomi, CDisplayEx, Panels).
"""

import os
import zipfile
from typing import List, Dict, Any

class CBZPackager:
    """
    Creates optimized CBZ archives from compressed page slices.
    """

    @staticmethod
    def create_cbz(
        output_path: str,
        processed_pages: List[Dict[str, Any]],
        compress_level: int = 0
    ) -> int:
        """
        Writes all slices sequentially into a .cbz archive.
        Since individual image slices (WebP) are already internally compressed,
        we use ZIP_STORED (compress_level=0) for maximum speed and zero CPU overhead.
        """
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        slice_counter = 0
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_STORED) as zf:
            for page_idx, page in enumerate(processed_pages, 1):
                slices = page.get("slices", [])
                for s in slices:
                    slice_counter += 1
                    data = s["data"]
                    # Determine extension based on magic bytes
                    if data[:2] == b'\xff\xd8':
                        ext = ".jpg"
                    elif data[:4] == b'RIFF':
                        ext = ".webp"
                    elif data[:8] == b'\x89PNG\r\n\x1a\n':
                        ext = ".png"
                    else:
                        ext = ".bin"
                        
                    entry_name = f"page_{slice_counter:04d}{ext}"
                    zf.writestr(entry_name, data)

        return os.path.getsize(output_path)

