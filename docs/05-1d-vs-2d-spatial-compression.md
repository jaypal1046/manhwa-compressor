# 05. The 1D vs. 2D Dimensionality Gap & Non-AI Compression Angles

Why do general-purpose compressors (ZIP, 7z, Gzip, Zstandard) fail to compress raw image panels? The answer lies in the fundamental divide between **1-Dimensional byte streams** and **2-Dimensional spatial grids**.

---

## 1. The 1D vs. 2D Dimensionality Trap

General compression algorithms were engineered for **1-Dimensional data**:
* Text files, JSON, source code, database dumps, and compiled binaries.
* In 1D data, symbols flow sequentially: `Character 1 -> Character 2 -> Character 3`.
* If a word or phrase repeats, it repeats **nearby in the linear stream**.

### The Flattening Problem in 2D Images
An image is a **2-Dimensional spatial matrix**:

```
        X (Width = 800 px)
       ┌───────────────────────────────┐
       │ P(0,0)   P(1,0)  ...  P(799,0)│  <── Row 0
Y      │ P(0,1)   P(1,1)  ...  P(799,1)│  <── Row 1
(Height│ P(0,2)   P(1,2)  ...  P(799,2)│  <── Row 2
=20k)  │   ...      ...   ...    ...   │
       └───────────────────────────────┘
```

In 2D space, pixel `P(0,1)` is **physically adjacent (1 pixel distance)** to pixel `P(0,0)` directly above it. In digital art, vertical neighbors share identical or near-identical color values.

However, computer memory, disks, and file streams are strictly **1-Dimensional**:

```
Linear Byte Stream:
[ Row 0: 2,400 bytes ] ──► [ Row 1: 2,400 bytes ] ──► [ Row 2: 2,400 bytes ]
▲                          ▲
P(0,0)                     P(0,1)
│                          │
└────── 2,400 bytes! ──────┘
```

* For an 800-pixel-wide 24-bit RGB image, the pixel directly above is **2,400 bytes away** in the file stream!
* A generic 1D compression engine (like LZ77/Deflate with a standard 32 KB sliding window) can barely look back a few rows.
* Because the 1D compressor doesn't know the image width or stride, it treats the spatial correlation as random, high-entropy noise.

---

## 2. Non-AI Mathematical "Angles" for Binary Data

Before resorting to heavy neural networks, computer science developed brilliant mathematical angles to expose hidden patterns in data:

### A. The Key-Value / Dictionary Angle & "The Dictionary Tax"
* **Mechanism (LZ77 / LZW / Byte-Pair Encoding):** Replaces recurring sequences with a shorter Key ID.
* **The Mathematical Constraint:** 
  $$\text{Total Encoded Size} = \text{Sequence of Keys} + \text{Key-to-Value Codebook}$$
* If data contains massive diversity (each pixel chunk is slightly different due to digital gradients or noise), the codebook table becomes larger than the raw data itself.
* **The Breakthrough:** Adaptive sliding dictionaries (LZ77) avoid storing a static table by using relative historical offsets instead.

### B. The Permutation Angle: Burrows-Wheeler Transform (BWT)
* **Used in:** `bzip2`.
* **Mechanism:** Takes a block of data, generates all circular cyclical shifts, and sorts them lexicographically.
* **Result:** It groups identical bytes together without losing a single bit of information. It requires **zero machine learning**, is **100% reversible**, and transforms scattered symbols into long, easily compressible runs of identical bytes.

### C. The Continuous Interval Angle: Arithmetic & Range Coding
* **Used in:** Modern JPEG (arithmetic mode), WebP, JPEG 2000.
* **Mechanism:** Instead of assigning discrete bit codes (e.g., Huffman trees where a symbol must take at least 1 whole bit), Arithmetic Coding treats the entire file as a **single arbitrary-precision fractional number** between `0.0` and `1.0`.
* High-probability symbols shrink the interval minimally; low-probability symbols shrink it heavily. It operates right at the mathematical Shannon entropy boundary.

### D. The Geometric Self-Similarity Angle: Fractal Compression
* **Mechanism:** Expresses image patches through **Affine Transformations** (scaling, rotating, translating, and adjusting brightness).
* Discards pixel grids entirely and stores mathematical contractive mapping equations.

---

## 3. True Pixel-Native Compression

To achieve high compression on manhwa without blurring, the compressor must be **dimensionally aware**:

1. **Spatial Neighbor Prediction (Paeth / Delta Filters):**
   Predict current pixel $X$ from its three neighbors ($A$ = left, $B$ = above, $C$ = upper-left):
   $$\hat{X} = A + B - C$$
   Storing only the prediction residual $(X - \hat{X})$ converts solid backgrounds and uniform line art into continuous streams of zeros.
2. **Space-Filling Fractal Curves (Hilbert Curves):**
   Instead of rasterizing row-by-row (which destroys vertical locality), traversal follows a 2D recursive space-filling curve. Pixels that are spatial neighbors in 2D remain neighbors in the 1D serialized sequence.

