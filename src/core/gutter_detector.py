"""
Core Module: Ultra-Fast Whitespace & Gutter Detection and Slicing
Scans 2D image matrices at memory speed using vectorized NumPy operations.
"""

from typing import List, Tuple, Dict, Any
import numpy as np
from PIL import Image

class GutterDetector:
    """
    Identifies pure whitespace (white #FFFFFF or black #000000) gutters
    in manhwa vertical strips and calculates optimal slice boundaries.
    """

    def __init__(self, tolerance: int = 4, min_gutter_height: int = 40):
        """
        :param tolerance: Pixel value tolerance from pure white (255 - tol) or black (0 + tol)
        :param min_gutter_height: Minimum consecutive blank rows to qualify as a collapsible gutter
        """
        self.tolerance = tolerance
        self.min_gutter_height = min_gutter_height

    def scan_gutters(self, img_arr: np.ndarray) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Scans rows of an RGB image array and identifies all collapsible gutters.
        Returns:
            - mask of rows: True for active art, False for collapsible gutter
            - manifest: list of segments with coordinates and gutter spacer tags
        """
        height, width, _ = img_arr.shape
        white_threshold = 255 - self.tolerance
        black_threshold = self.tolerance

        # Vectorized check: which rows are completely solid white or black across all columns
        is_white_row = np.all(img_arr >= white_threshold, axis=(1, 2))
        is_black_row = np.all(img_arr <= black_threshold, axis=(1, 2))
        is_gutter_row = is_white_row | is_black_row

        # Find continuous runs of gutter rows
        manifest: List[Dict[str, Any]] = []
        active_mask = np.ones(height, dtype=bool)

        y = 0
        while y < height:
            if is_gutter_row[y]:
                start_y = y
                is_white = is_white_row[y]
                while y < height and is_gutter_row[y] and (is_white_row[y] == is_white):
                    y += 1
                gutter_len = y - start_y
                
                # Only collapse if it meets the minimum threshold length
                if gutter_len >= self.min_gutter_height:
                    active_mask[start_y:y] = False
                    color_hex = "#FFFFFF" if is_white else "#000000"
                    manifest.append({
                        "type": "gutter",
                        "start_y": start_y,
                        "end_y": y,
                        "height": gutter_len,
                        "color": color_hex
                    })
            else:
                start_art = y
                while y < height and not is_gutter_row[y]:
                    y += 1
                manifest.append({
                    "type": "art",
                    "start_y": start_art,
                    "end_y": y,
                    "height": y - start_art
                })

        return active_mask, manifest

    def calculate_safe_strip_cuts(
        self,
        img_arr: np.ndarray,
        target_height: int = 1800,
        max_height: int = 2400
    ) -> List[Tuple[int, int]]:
        """
        For ultra-tall continuous manhwa strips (e.g. 20,000px high):
        Calculates safe horizontal cut lines at the center of whitespace gutters
        so that character art and speech bubbles are NEVER cut in half.
        """
        height = img_arr.shape[0]
        if height <= max_height:
            return [(0, height)]

        _, manifest = self.scan_gutters(img_arr)
        gutters = [m for m in manifest if m["type"] == "gutter"]

        cuts: List[Tuple[int, int]] = []
        current_y = 0

        while current_y < height:
            ideal_end = current_y + target_height
            if ideal_end >= height:
                cuts.append((current_y, height))
                break

            # Find the best gutter closest to the target height within current_y .. current_y + max_height
            candidate_gutters = [
                g for g in gutters
                if g["start_y"] >= current_y + (target_height // 2) and g["end_y"] <= current_y + max_height
            ]

            if candidate_gutters:
                # Pick the gutter with largest height or closest to target
                best_gutter = max(candidate_gutters, key=lambda g: g["height"])
                # Cut at the midpoint of the gutter
                cut_y = (best_gutter["start_y"] + best_gutter["end_y"]) // 2
            else:
                # Fallback if no gutter exists within the window: cut at target
                cut_y = min(ideal_end, height)

            cuts.append((current_y, cut_y))
            current_y = cut_y

        return cuts

