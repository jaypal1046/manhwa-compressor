# 03. Data-Storage Level Solutions (No Blurring, No Slow Re-encoding)

Lossy algorithms "cheat" by discarding visual data and blurring text. At the same time, re-encoding hundreds of high-resolution images using heavy modern encoders (like slow-mode WebP/AVIF) burns excessive CPU time.

This document details **pure data storage and systems-level solutions** that achieve high compression without degrading image quality or causing processing bottlenecks.

---

## 1. Sparse Tiling & Whitespace Gutter Pruning

### The Concept
A typical manhwa chapter contains **30% to 50% empty vertical space**—pure white (`#FFFFFF`) or pure black (`#000000`) spacer gutters designed to pace the reading experience on mobile screens.

Standard image files allocate data bytes across every single pixel of those gutters.

```
Original Strip (20,000px high)           Sparse Tile Model
┌───────────────────────────────┐        ┌───────────────────────────────┐
│ [Panel 1 Artwork]             │        │ Tile 0: Panel 1 Blob          │
├───────────────────────────────┤        ├───────────────────────────────┤
│                               │        │                               │
│ Empty White Gutter            │ ─────► │ Sparse Gap (Stored as:        │
│ (2,500px pure white)          │        │ "Offset: Y=4500, Height=2500, │
│                               │        │  Color=#FFFFFF" -> 8 bytes!)  │
├───────────────────────────────┤        ├───────────────────────────────┤
│ [Panel 2 Artwork]             │        │ Tile 1: Panel 2 Blob          │
└───────────────────────────────┘        └───────────────────────────────┘
```

### The Engineering Solution
1. **Vertical Whitespace Scanning:** Run a fast row-by-row pixel scan looking for rows where all pixels match `#FFFFFF` (or `#000000`) within a small tolerance.
2. **Gutter Extraction:** Separate the continuous strip into discrete artwork bounding boxes and gutter metadata.
3. **Storage Representation:**
   * Store only the artwork slices.
   * Store a tiny JSON/binary metadata manifest recording the vertical gutter gaps.
4. **Reconstruction / Rendering:** The reader or PDF builder dynamically stretches the blank background according to the manifest.
5. **Efficiency:**
   * **Size reduction:** **30% to 50%** cut immediately.
   * **Visual loss:** **0.00% (Mathematically identical).**
   * **CPU Cost:** Extremely low (single-pass linear memory scan, no complex matrix transforms).

---

## 2. Content-Defined Chunking & Binary Deduplication (FastCDC)

### The Concept
When storing multi-chapter archives or entire manhwa series, massive binary duplication exists:
* Scanlation group credit pages, recruitment banners, and warning screens are repeated across every single chapter.
* Webtoon creators heavily reuse background 3D SketchUp assets (castles, furniture, streetscapes) and standardized sound-effect art.

### The Engineering Solution
Using **Fast Content-Defined Chunking (FastCDC)**:
1. Divide raw image data streams into variable-sized cryptographic chunks based on rolling hash boundaries (e.g., Gear hash).
2. Calculate the SHA-256 hash of each chunk.
3. Store unique chunks in a global content-addressable block store.
4. Duplicate blocks are replaced with a 32-byte hash pointer.

### Efficiency
* **Multi-chapter storage savings:** **20% to 35%** across 50+ chapters.
* **Pixel manipulation:** None.
* **Extraction:** Restores the exact byte-for-byte original file.

---

## 3. Lossless Bitstream Optimization (Zero Re-rendering)

### The Concept
Re-encoding an image requires:
$$\text{Bitstream} \xrightarrow{\text{Decode}} \text{RGB Bitmaps in RAM} \xrightarrow{\text{Transforms}} \text{Quantization} \xrightarrow{\text{Re-encode}} \text{New File}$$
This is computationally expensive and introduces generational loss.

**Bitstream Optimization** operates directly on the compressed entropy stream without decoding pixels to RGB.

### Key Tools & Methods
1. **Huffman Table Rebuilding (`jpegtran` / `mozjpeg` lossless mode):**
   * Parses existing JPEG markers and optimizes the Huffman code trees for the specific image's frequency distribution.
   * Strips non-standard EXIF metadata, ICC color profiles, and thumbnail caches.
   * **Speed:** Disk I/O limited (500+ MB/s).
   * **Loss:** **0.00% bit-for-bit identical pixel reconstruction.**
   * **Savings:** 8% to 18% reduction.
2. **DEFLATE Optimization (`ECT` / `oxipng`):**
   * For PNG panels, replaces standard zlib compression with brute-force LZ77 window search and optimal Huffman tree construction.
   * **Savings:** 15% to 35% reduction on raw PNGs with zero pixel alterations.

---

## 4. Perceptually Lossless Strategy (When Format Conversion is Desired)

If format conversion is permissible and the goal is maximum size reduction without text blurring:

| Technique | Setting | Why it prevents degradation |
| :--- | :--- | :--- |
| **WebP Lossy** | `-q 80 -sharp_yuv -m 4` | Intra-prediction handles flat areas; `sharp_yuv` preserves crisp typography boundaries. |
| **MozJPEG** | `Q=82, subsampling=0` | Forcing `4:4:4` chroma ensures text bubbles and colored line art never bleed. |
| **JPEG XL Lossless** | `cjxl input.jpg output.jxl --lossless_jpeg=1` | Re-packs JPEG entropy losslessly; saves ~20% with exact byte-for-byte restoration. |

