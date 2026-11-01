# Manhwa & Comic Compression Engine - Research & Architecture Documentation

This repository documents the research, core engineering principles, and actionable architectures for building a high-efficiency **Manhwa / Comic Compression System**.

---

## 📌 The Core Problem

Standard compression systems (such as generic PDF compressors, standard ZIP/7z archives, and lossy JPEG encoders) were engineered for either **office documents (vector text + low-DPI photos)** or **natural photographic images**.

Digital Manhwa / Webtoons represent a unique media format:
1. **100% Rasterized**: Speech bubbles, typography, and line art are embedded directly into raw pixels (zero vector text layers).
2. **Extreme Aspect Ratios**: Tall continuous vertical strips (often $800 \times 15,000$ to $30,000+$ pixels).
3. **High-Contrast Step Transitions**: Pure black dialogue ink directly bordering pure white speech bubbles.
4. **Vast Solid Gutters**: 30% to 50% of the entire file consists of empty white (`#FFFFFF`) or black (`#000000`) spacer gutters.

When standard compressors process manhwa:
- **Lossy compressors cheat by blurring**, causing severe mosquito noise / ringing around speech bubbles, making dialogue unreadable.
- **Heavy modern re-encoders (WebP/AVIF)** deliver great ratios but are **computationally expensive and slow**, burning massive CPU time across multi-chapter archives.
- **Generic archivers (ZIP/7z)** fail due to Shannon's Entropy Limit because existing JPEG/PNG streams are already high-entropy.

---

## 📂 Documentation Index

| Document | Topic | Description |
| :--- | :--- | :--- |
| **[01. PDF Compression Internals](./01-pdf-compression-internals.md)** | Engine Internals | How PDF object streams, FlateDecode, DCTDecode, and JBIG2 work under the hood. |
| **[02. Manhwa & Comic Pitfalls](./02-manhwa-compression-challenges.md)** | Failure Modes | Why speech bubbles blur, why canvas memory overflows, and why chroma subsampling ruins line art. |
| **[03. Data-Storage Level Solutions](./03-storage-level-solutions.md)** | Pure Systems Approach | Sparse tiling, gutter elimination, binary deduplication (FastCDC), and lossless bitstream optimization. |
| **[04. Implementation Roadmap](./04-implementation-roadmap.md)** | Engineering Blueprint | Architecture design, pipeline stages, algorithm decision matrix, and CLI/API roadmap. |
| **[05. 1D vs. 2D Spatial Dimensionality](./05-1d-vs-2d-spatial-compression.md)** | The Core Breakthrough | Why 1D text/database compressors fail on 2D images, row-stride distance, and non-AI mathematical transforms. |
| **[06. What Can We Do Better?](./06-novel-manhwa-compression-engine.md)** | Novel Engine Design | Dual-layer MRC (Mixed Raster Content) text protection, 2D pre-conditioning delta filters, and gutter collapsing. |

---

## 🎯 Quick Comparison Matrix

| Approach | Speed / CPU Load | Quality Loss | Size Reduction (Typical) | Best Used For |
| :--- | :--- | :--- | :--- | :--- |
| **Standard PDF Compressor** | Medium | ❌ Blurry text, severe ringing | 30% – 50% | General office documents (NOT manhwa) |
| **Heavy Re-encode (WebP Q=82)** | ❌ Slow (High CPU) | Low (Perceptually clean) | **75% – 85%** | Final mobile distribution (.cbz) |
| **2D Stride Pre-Filter + Zstd** | ⚡ Ultra Fast | **Zero (100% exact)** | **60% – 75%** | Ultra-fast lossless chapter archiving |
| **Sparse Tiling (Gutter Pruning)** | ⚡ Ultra Fast | **Zero (100% exact)** | **30% – 50%** | Webtoon vertical scroll storage |
| **Dual-Layer MRC Segmentation** | Medium | **Zero on Text** (Sharp vector-grade) | **85% – 90%** | The ultimate manhwa comic standard |
| **Binary Deduplication (FastCDC)** | ⚡ Fast (I/O bound) | **Zero (100% exact)** | **20% – 35% across volumes** | Multi-chapter archive servers & databases |
| **Bitstream Optimization (Huffman)** | ⚡ Instant (Disk speed) | **Zero (100% exact)** | **10% – 20%** | Lossless optimization of existing JPEGs |
