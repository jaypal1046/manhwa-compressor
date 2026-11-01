# 04. Implementation Roadmap & Architecture Blueprint

This document outlines the software architecture and implementation plan for the **Manhwa & Comic Compression Plugin / Tool**.

---

## 1. System Pipeline Architecture

```
                    ┌────────────────────────────┐
                    │      Source Manhwa         │
                    │   (PDF / CBZ / ZIP / Raw)  │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │      1. Ingestion Engine   │
                    │  Extracts strips to stream │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │   2. Structural Profiler   │
                    │  • Dimension check         │
                    │  • Whitespace gutter scan  │
                    │  • Format & entropy probe  │
                    └─────────────┬──────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Mode 1: Pure   │      │  Mode 2: Fast   │      │  Mode 3: Mobile │
│  Data Storage   │      │  Gutter Pruning │      │  WebP / CBZ     │
├─────────────────┤      ├─────────────────┤      ├─────────────────┤
│ • Bitstream opt │      │ • Strip gutters │      │ • Slice strips  │
│ • Deduplication │      │ • Sparse tiles  │      │ • WebP Q=82     │
│ • No re-encode  │      │ • Metadata map  │      │ • sharp_yuv     │
└────────┬────────┘      └────────┬────────┘      └────────┬────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │  4. Packaging & Output     │
                    │  • CBZ (Zip archive)       │
                    │  • Optimized PDF (UserUnit)│
                    └────────────────────────────┘
```

---

## 2. Processing Modes & Use-Case Mapping

### Mode 1: "Data Storage / Exact" (Zero Quality Loss, Instant Speed)
* **Goal:** Maximum speed, zero CPU lag, zero pixel alterations.
* **Pipeline:**
  1. Extract existing JPEG/PNG streams directly from PDF or ZIP without rendering.
  2. Run lossless bitstream Huffman optimization (`jpegtran`/`oxipng`).
  3. Deduplicate recurring banners/credits across chapters.
* **Output:** Cleaned CBZ / PDF.

### Mode 2: "Sparse Gutter Pruning" (30–50% Cut, 100% Exact Pixels)
* **Goal:** Cut file size by eliminating empty whitespace gutters without touching visual artwork.
* **Pipeline:**
  1. Fast single-channel row scan to locate continuous horizontal strips of `#FFFFFF` or `#000000`.
  2. Extract only active panel regions.
  3. Store gutter heights in a lightweight manifest.
* **Output:** Manifest-backed archive or rebuilt compact PDF with scaled vertical offsets.

### Mode 3: "Perceptually Lossless Mobile" (75–85% Cut, Crisp Text)
* **Goal:** Maximum compression for phones and e-readers without speech bubble blurring.
* **Pipeline:**
  1. Slice continuous 20,000px strips at safe white gutter intervals into standard 1600px–2000px height segments.
  2. Encode slices using **WebP (Q=80–82, `sharp_yuv=True`)** or **MozJPEG (Q=82, Chroma 4:4:4)**.
  3. Assemble into `.cbz` (or standard PDF with correct bounding boxes).

---

## 3. Recommended Codebase Structure

```
pdf_manwha_compress_zip/
├── docs/
│   ├── README.md
│   ├── 01-pdf-compression-internals.md
│   ├── 02-manhwa-compression-challenges.md
│   ├── 03-storage-level-solutions.md
│   └── 04-implementation-roadmap.md
├── src/
│   ├── __init__.py
│   ├── cli.py                     # Command-line interface
│   ├── core/
│   │   ├── analyzer.py            # Image dimensions, entropy, gutters
│   │   ├── gutter_detector.py     # Whitespace row scanning & slicing
│   │   ├── deduplicator.py        # Hash-based panel deduplication
│   │   ├── bitstream_optimizer.py # Lossless Huffman & stream tools
│   │   └── reencoder.py           # WebP sharp_yuv / MozJPEG 4:4:4
│   └── packagers/
│       ├── cbz_packager.py        # CBZ archive generation
│       └── pdf_packager.py        # PDF builder with UserUnit handling
├── tests/
│   └── ...
└── requirements.txt
```

---

## 4. Next Steps & Development Phases

1. **Phase 1: Ingestion & Profiler**
   * Build scripts to extract images directly from PDFs and ZIPs without decompressing pixel data unless necessary.
2. **Phase 2: Gutter Scanning Algorithm**
   * Write an ultra-fast NumPy/Pillow linear row scanner to identify solid whitespace boundaries.
3. **Phase 3: Lossless Bitstream & WebP Sharp Pipeline**
   * Implement both the non-reencoding bitstream path and the sharp-chroma WebP path.
4. **Phase 4: Packaging & Benchmarking**
   * Output `.cbz` and `.pdf`, running automated file size and perceptual quality (SSIM/Butteraugli) comparisons.

