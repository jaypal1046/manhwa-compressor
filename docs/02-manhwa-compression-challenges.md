# 02. Manhwa & Comic Compression Challenges

When standard compression algorithms (or generic online PDF optimizers) process manhwa or comics, severe degradation occurs. This document details each specific failure mode and the underlying mathematical reasons.

---

## 1. Speech Bubble Text Blurring (DCT Ringing & Mosquito Noise)

### The Mechanism
Standard compressors apply lossy **`/DCTDecode` (JPEG)** with aggressive quantization to shrink image size. 
* The Discrete Cosine Transform operates on **$8 \times 8$ pixel blocks**.
* It transforms spatial pixel variations into frequency coefficients (low-frequency base colors vs. high-frequency sharp details).
* Quantization discards high-frequency coefficients first because the human visual system is less sensitive to fine high-frequency noise in natural photographs.

### The Failure in Manhwa
Speech bubbles consist of **pure black high-contrast letter outlines bordering pure white backgrounds**:
* This represents a mathematical step discontinuity (infinite frequency gradient).
* When high-frequency coefficients are truncated by quantization, the inverse DCT cannot reconstruct the sharp boundary.
* The result is **Gibbs Phenomenon** (ringing artifacts / mosquito noise): fuzzy, noisy halos surrounding every single letter. At mobile reading sizes, dialogue becomes blurry and strenuous to read.

---

## 2. Chroma Subsampling Degradation (`4:2:0` Color Bleeding)

### The Mechanism
Natural photography compressors convert RGB to **YCbCr**:
* **Y (Luma)**: Brightness detail (retained at 100%).
* **Cb / Cr (Chroma)**: Blue-difference and red-difference color channels.
* In standard `4:2:0` subsampling, color resolution is cut in half horizontally and vertically (1 color sample shared across a $2 \times 2$ pixel quad).

### The Failure in Manhwa
* Digital comics rely heavily on colored outlines, colored speech bubbles (shouts, system notifications), and fine colored line art.
* Under `4:2:0` subsampling, color edges bleed across black line borders into adjacent background areas.
* Sharp colored typography becomes muddy and loses legibility.

---

## 3. Huge Canvas Memory Overhead & Dimension Limits

### The Mechanism
Manhwa is produced as continuous vertical scrolls. A single chapter file often consists of images measuring **$800 \times 20,000$ to $35,000$ pixels**.

### The Failure
1. **RAM Buffering:** When a standard PDF engine decompresses a raster strip to render or optimize it, it must allocate an uncompressed 24-bit raw bitmap:
   $$\text{RAM} = \frac{800 \times 30,000 \times 3 \text{ bytes}}{1024 \times 1024} \approx 68.6 \text{ MB per strip}$$
   Processing 10 such strips concurrently triggers out-of-memory (OOM) exceptions on constrained devices or worker nodes.
2. **PDF Specification Limits:** In the standard PDF 1.7 specification:
   * The default maximum page dimension is **$14,400 \times 14,400$ points** ($200 \times 200$ inches at 72 points/inch).
   * Strips taller than 14,400 points must employ the `/UserUnit` dictionary key to scale the coordinate space.
   * Generic PDF compressors often omit `/UserUnit` handling, resulting in truncated pages, aspect ratio stretching, or complete rendering errors.

---

## 4. Screentone Moiré Patterns (Manga & Halftone Art)

### The Mechanism
In traditional manga and styled comic art, shading is created using fine dot grids (**halftone screentones**).

### The Failure
* Standard downsampling filters (Bicubic, Bilinear) resample pixel coordinates uniformly across a fixed grid.
* When the downsampling sampling frequency interferes with the regular spacing of the screentone dots, **aliasing occurs**.
* This generates large, distracting wave-like interference patterns (**Moiré bands**) across character shadows and backgrounds.

---

## 5. Color Banding in Digital Gradients

### The Mechanism
Webtoons feature heavy digital painting effects: magic auras, glows, sunset skies, and vignette lighting transitions.

### The Failure
* Aggressive color-space quantization (e.g., attempting to quantize to 8-bit indexed palettes or excessive JPEG luma quantization) collapses smooth 24-bit RGB gradients into discrete steps.
* Smooth atmospheric lighting turns into harsh, visible contour lines (posterization).

