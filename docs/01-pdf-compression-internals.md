# 01. PDF Compression Internals: Under the Hood

To understand why standard PDF compression engines fail or corrupt manhwa and comics, we must first examine how a PDF is structured and how engines compress it.

---

## 1. The Anatomy of a PDF Document

A PDF is not a flat file; it is an **object-oriented directed graph** containing four basic structures:

```
[ Root / Catalog Dictionary ]
            │
            ▼
    [ Pages Tree ]
            │
            ├───────────────┬───────────────┐
            ▼               ▼               ▼
        [ Page 1 ]      [ Page 2 ]      [ Page N ]
            │
     ┌──────┴───────────────────────┐
     ▼                              ▼
[ Content Stream ]           [ Resources Dict ]
(Drawing commands, layout)          │
                             ┌──────┴──────┐
                             ▼             ▼
                         [ Fonts ]    [ XObjects ]
                                      (Images / Forms)
```

1. **Primitive Objects**: Booleans, integers, floating-point numbers, strings, names (`/Type`), arrays `[...]`, and dictionaries `<< ... >>`.
2. **Indirect Objects**: Defined with an object ID and generation number (e.g., `12 0 obj ... endobj`).
3. **Streams**: Binary byte payloads prefixed by a dictionary describing length and decompression filters.
4. **Cross-Reference Table (`xref`)**: Byte-offset indices pointing to every object in the file.

---

## 2. Standard PDF Compression Mechanisms

PDF compression engines (Acrobat Distiller, Ghostscript, `pdfcpu`, QPDF) operate across three layers:

### A. Stream Compression (`/Filter`)
Content streams and binary streams are passed through compression algorithms:

* **`/FlateDecode`**: The standard zlib/Deflate lossless algorithm (LZ77 + Huffman coding). Used for page layout instructions, vector draw paths, and font tables.
* **`/DCTDecode`**: Lossy baseline Discrete Cosine Transform (standard JPEG). Used for photographic raster images.
* **`/JPXDecode`**: JPEG 2000 wavelet-based compression (introduced in PDF 1.5). Allows both lossless and lossy modes without 8x8 block boundary artifacts.
* **`/CCITTFaxDecode` & `/JBIG2Decode`**: Bi-level (1-bit monochrome) algorithms. JBIG2 uses pattern-matching symbol dictionaries (ideal for scanned black-and-white text pages).

### B. Structural Consolidation (PDF 1.5+ Object Streams)
* **Object Streams (`/ObjStm`)**: Instead of storing hundreds of individual small indirect objects scattered across the file, the engine packs them sequentially into a single data stream and applies `/FlateDecode` across all of them.
* **Cross-Reference Streams (`/XRef`)**: Replaces ASCII xref tables with compressed binary streams.
* **Dead Object Elimination**: Compaction passes traverse the object graph from the `/Root` catalog, discarding unreferenced objects, historical version revisions, and internal edit histories.

### C. Font Subsetting
* When true vector text is present, engines strip unused glyphs. If a document uses 35 characters from an 8 MB TrueType font, the engine subsets the font down to ~15 KB.

### D. Image Resampling & Quantization
* High-resolution photographic images are downsampled to standard target resolutions (e.g., 300 DPI for print $\rightarrow$ 150 DPI for e-readers $\rightarrow$ 72 DPI for web).
* Color channels are converted to YCbCr, and chroma subsampling (`4:2:0`) is applied to halve the color resolution.

---

## 3. The Core Mismatch with Manhwa

Standard PDF engines operate under assumptions that are completely violated by digital manhwa:

| Standard PDF Assumption | Reality in Manhwa / Webtoon |
| :--- | :--- |
| Text is vector-based and can be subsetted. | **Text is 100% baked into raster image pixels.** |
| Images are supplementary illustrations/photos. | **The entire document is a continuous sequence of gigantic images.** |
| Pages follow standardized aspect ratios (A4/Letter). | **Pages are ultra-long vertical scrolling strips (e.g., 800×25,000px).** |
| Lossy compression can safely discard high-frequency color info. | **Dialogue bubbles contain sharp high-frequency edges; discarding them causes unreadable text.** |

