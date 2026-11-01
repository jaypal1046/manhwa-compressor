"""
Core Module: 2D Stride Pre-Conditioning Filter
Applies vertical spatial delta filtering to 2D image matrices before compression.
100.000% Lossless and mathematically reversible using modulo-256 arithmetic.
"""

import numpy as np

class StrideFilter2D:
    """
    Transforms 2D spatial pixel redundancy into contiguous runs of 0x00 bytes.
    Enables general-purpose entropy encoders (Zstd, Deflate, LZMA2) to achieve
    significantly higher compression ratios on raw pixel matrices.
    """

    @staticmethod
    def encode(img_arr: np.ndarray) -> np.ndarray:
        """
        Applies vertical 2D difference: Delta[y] = Row[y] - Row[y-1] (mod 256).
        Row 0 is kept as the baseline header row.
        """
        assert img_arr.dtype == np.uint8, "Array must be uint8"
        encoded = np.empty_like(img_arr)
        encoded[0] = img_arr[0]
        # Modulo 256 subtraction is native to uint8 overflow/underflow
        encoded[1:] = img_arr[1:] - img_arr[:-1]
        return encoded

    @staticmethod
    def decode(delta_arr: np.ndarray) -> np.ndarray:
        """
        Reverses the vertical difference using cumulative sum modulo 256.
        Restores the exact, bit-for-bit identical original pixel array.
        """
        assert delta_arr.dtype == np.uint8, "Delta array must be uint8"
        # Cumulative sum along axis 0 (rows) modulo 256 reproduces original rows
        return np.cumsum(delta_arr, axis=0, dtype=np.uint8)

    @staticmethod
    def encode_2d_horizontal_vertical(img_arr: np.ndarray) -> np.ndarray:
        """
        Dual-axis 2D delta: First vertical difference, then horizontal difference.
        Creates an even higher concentration of exact zeros.
        """
        # Step 1: Vertical delta
        v_delta = StrideFilter2D.encode(img_arr)
        # Step 2: Horizontal delta along columns
        h_delta = np.empty_like(v_delta)
        h_delta[:, 0] = v_delta[:, 0]
        h_delta[:, 1:] = v_delta[:, 1:] - v_delta[:, :-1]
        return h_delta

    @staticmethod
    def decode_2d_horizontal_vertical(delta_arr: np.ndarray) -> np.ndarray:
        """
        Reverses dual-axis 2D delta (horizontal first, then vertical).
        """
        # Step 1: Invert horizontal delta
        v_delta = np.cumsum(delta_arr, axis=1, dtype=np.uint8)
        # Step 2: Invert vertical delta
        return np.cumsum(v_delta, axis=0, dtype=np.uint8)

