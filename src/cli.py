"""
Command-Line Interface & Orchestrator: Fast Manhwa Compression Engine
Supports:
1. Single Chapter / Image Compression (CBZ & PDF)
2. Direct Archive Recompression (CBZ/ZIP -> CBZ/PDF)
3. PDF Ingestion & Re-creation (PDF -> PDF or PDF -> CBZ)
4. Batch Library Processing (--batch)
5. Automated Background Server Watcher (--watch)
6. Instant Archive Decompression (--decompress)
"""

import os
import sys
import time
import argparse
import zipfile
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional
from PIL import Image

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

# Support both direct execution and module import
try:
    from .core.fast_encoder import FastPageEncoder, CompressionPreset
    from .core.pdf_processor import PDFProcessor
    from .packagers.cbz_packager import CBZPackager
    from .packagers.pdf_packager import PDFPackager
    from .watcher import FolderWatcher
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.core.fast_encoder import FastPageEncoder, CompressionPreset
    from src.core.pdf_processor import PDFProcessor
    from src.packagers.cbz_packager import CBZPackager
    from src.packagers.pdf_packager import PDFPackager
    from src.watcher import FolderWatcher

def process_single_file(file_path: str, encoder: FastPageEncoder):
    """Processes a single image file using the encoder."""
    try:
        return encoder.process_file_path(file_path)
    except Exception as e:
        print(f"[Warning] Skipped corrupt/invalid file '{file_path}': {e}", file=sys.stderr)
        return None

def process_chapter(image_paths: List[str], output_path: str, encoder: FastPageEncoder, workers: int = 8) -> int:
    """
    Compresses a list of images into the specified output format (.cbz or .pdf).
    """
    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(lambda p: process_single_file(p, encoder), image_paths))
        
    valid_results = [r for r in results if r is not None]
    if not valid_results:
        raise ValueError(f"No valid images could be processed for '{output_path}'")
        
    output_ext = os.path.splitext(output_path)[1].lower()
    if output_ext == ".pdf":
        return PDFPackager.create_pdf(output_path, valid_results)
    else:
        return CBZPackager.create_cbz(output_path, valid_results)

def run_batch_mode(input_dir: str, output_dir: str, encoder: FastPageEncoder, workers: int = 8, out_format: str = "cbz"):
    """
    Processes multiple chapter subfolders or archives in bulk.
    """
    os.makedirs(output_dir, exist_ok=True)
    entries = sorted(os.listdir(input_dir))
    
    # Filter chapters (directories or existing archives)
    chapters = [
        e for e in entries
        if (os.path.isdir(os.path.join(input_dir, e)) or e.lower().endswith(('.cbz', '.zip', '.pdf')))
        and not e.startswith('.')
    ]
    
    if not chapters:
        print(f"No chapter directories or archives found in '{input_dir}'", file=sys.stderr)
        return

    print("=" * 68)
    print(f"      BATCH COMPRESSION MODE: {len(chapters)} CHAPTERS")
    print("=" * 68)
    print(f"Source Directory : {input_dir}")
    print(f"Output Directory : {output_dir}")
    print(f"Target Format    : .{out_format.upper()}")
    print("-" * 68)

    t_batch = time.time()
    total_orig = 0
    total_out = 0

    for idx, ch_name in enumerate(chapters, 1):
        ch_path = os.path.join(input_dir, ch_name)
        base_name = os.path.splitext(ch_name)[0]
        out_file = os.path.join(output_dir, f"{base_name}.{out_format}")
        
        t0 = time.time()
        
        # Case A: Subdirectory of images
        if os.path.isdir(ch_path):
            images = []
            for root, _, files in os.walk(ch_path):
                for f in sorted(files):
                    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp')):
                        images.append(os.path.join(root, f))
            if not images:
                continue
            ch_orig_sz = sum(os.path.getsize(img) for img in images)
            sz = process_chapter(images, out_file, encoder, workers=workers)
            
        # Case B: PDF archive
        elif ch_name.lower().endswith('.pdf'):
            ch_orig_sz = os.path.getsize(ch_path)
            if out_format == "pdf":
                stats = PDFProcessor.process_pdf_to_pdf(ch_path, out_file, encoder=encoder)
                sz = stats["compressed_size"]
            else:
                pages = PDFProcessor.extract_pages_from_pdf(ch_path)
                slices = []
                for p in pages:
                    if encoder.simd_engine:
                        data, mode = encoder.simd_engine.encode_tile(p)
                    elif HAS_OPENCV:
                        _, enc = cv2.imencode(".jpg", p, [cv2.IMWRITE_JPEG_QUALITY, 80])
                        data = enc.tobytes()
                    else:
                        continue
                    slices.append({"data": data, "width": p.shape[1], "height": p.shape[0]})
                sz = CBZPackager.create_cbz(out_file, [{"slices": slices}])
                
        # Case C: ZIP/CBZ archive
        else:
            ch_orig_sz = os.path.getsize(ch_path)
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(ch_path, 'r') as zf:
                    zf.extractall(temp_dir)
                images = []
                for root, _, files in os.walk(temp_dir):
                    for f in sorted(files):
                        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp')):
                            images.append(os.path.join(root, f))
                if not images:
                    continue
                sz = process_chapter(images, out_file, encoder, workers=workers)

        total_orig += ch_orig_sz
        total_out += sz
        elapsed = time.time() - t0
        cut_pct = (1.0 - sz / max(ch_orig_sz, 1)) * 100
        print(f"[{idx:02d}/{len(chapters):02d}] {base_name:30s} : {ch_orig_sz/(1024*1024):5.1f}MB -> {sz/(1024*1024):5.1f}MB ({cut_pct:4.1f}% cut) in {elapsed:.2f}s")

    total_time = time.time() - t_batch
    total_cut = (1.0 - total_out / max(total_orig, 1)) * 100
    print("-" * 68)
    print("      BATCH COMPRESSION COMPLETE")
    print("-" * 68)
    print(f"Total Time Taken   : {total_time:.2f} seconds ({len(chapters)/max(total_time,0.001):.1f} chapters/sec)")
    print(f"Total Storage Cut  : {total_orig/(1024*1024):.1f} MB -> {total_out/(1024*1024):.1f} MB (Saved {total_cut:.1f}%)")
    print("=" * 68)

def main():
    parser = argparse.ArgumentParser(
        description="Fast Manhwa & Comic Compression Engine (CBZ & PDF)"
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Input image paths, chapter directory, or archive file"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output path (.cbz, .pdf, or destination directory)"
    )
    parser.add_argument(
        "--watch",
        help="Start automated server watcher on specified directory"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Batch mode: compress all subfolders or archives in the input directory"
    )
    parser.add_argument(
        "--format",
        choices=["cbz", "pdf"],
        default="cbz",
        help="Target format for batch mode (default: cbz)"
    )
    parser.add_argument(
        "--decompress",
        action="store_true",
        help="Decompress an existing CBZ archive into image files"
    )
    parser.add_argument(
        "--preset",
        choices=["simd_adaptive", "simd_turbo", "turbo", "balanced", "max_quality", "lossless"],
        default="simd_adaptive",
        help="Compression preset: simd_adaptive (L3-Cache + Adaptive Chroma, ~0.38s!), simd_turbo, turbo, balanced, max_quality, lossless"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Number of parallel worker threads (default: 8)"
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="Target DPI for PDF rasterization/extraction (default: 150)"
    )

    args = parser.parse_args()

    preset_map = {
        "simd_adaptive": CompressionPreset.SIMD_ADAPTIVE,
        "simd_turbo": CompressionPreset.SIMD_TURBO,
        "turbo": CompressionPreset.TURBO,
        "balanced": CompressionPreset.BALANCED,
        "max_quality": CompressionPreset.MAX_QUALITY,
        "lossless": CompressionPreset.LOSSLESS_EXACT
    }
    encoder = FastPageEncoder(preset=preset_map[args.preset])

    # 1. Server Watcher Mode
    if args.watch:
        if not args.output:
            print("Error: --output directory is required when using --watch mode.", file=sys.stderr)
            sys.exit(1)
        watcher = FolderWatcher(
            watch_dir=args.watch,
            output_dir=args.output,
            encoder=encoder,
            target_format=args.format
        )
        watcher.start_watching()
        return

    # 2. Decompression Mode
    if args.decompress:
        if not args.inputs or not args.output:
            print("Error: Input archive and --output directory are required for decompression.", file=sys.stderr)
            sys.exit(1)
        cbz_file = args.inputs[0]
        out_dir = args.output
        os.makedirs(out_dir, exist_ok=True)
        
        print("=" * 68)
        print("      FAST DECOMPRESSION ENGINE")
        print("=" * 68)
        print(f"Archive to Decompress : {cbz_file}")
        print(f"Output Directory      : {out_dir}")
        print("-" * 68)
        
        t0 = time.time()
        with zipfile.ZipFile(cbz_file, "r") as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(('.webp', '.png', '.jpg', '.jpeg'))]
            for name in names:
                zf.extract(name, out_dir)
                
        elapsed = time.time() - t0
        print(f"Decompressed {len(names)} panels in {elapsed:.3f} seconds!")
        print(f"Panel Render Rate     : {len(names)/max(elapsed, 0.001):.1f} panels/sec")
        print("=" * 68)
        return

    if not args.inputs or not args.output:
        parser.print_help()
        sys.exit(1)

    # 3. Batch Multi-Chapter Mode
    if args.batch:
        input_dir = args.inputs[0]
        run_batch_mode(input_dir, args.output, encoder, workers=args.workers, out_format=args.format)
        return

    # Ensure output has a valid extension if not a directory
    output_ext = os.path.splitext(args.output)[1].lower()
    if not output_ext:
        args.output += ".cbz"
        output_ext = ".cbz"

    # 4. Handle single PDF as input (.pdf -> .pdf or .pdf -> .cbz)
    first_input = args.inputs[0]
    if len(args.inputs) == 1 and first_input.lower().endswith('.pdf') and os.path.isfile(first_input):
        if output_ext == '.pdf':
            print("=" * 68)
            print("      PDF-TO-PDF COMPRESSION ENGINE (PyMuPDF + SIMD)")
            print("=" * 68)
            print(f"Input PDF        : {first_input}")
            print(f"Target Output    : {args.output}")
            print(f"Preset           : {args.preset.upper()}")
            print("-" * 68)
            stats = PDFProcessor.process_pdf_to_pdf(first_input, args.output, encoder=encoder, dpi=args.dpi)
            print("-" * 68)
            print("      PDF COMPRESSION COMPLETE")
            print("-" * 68)
            print(f"Pages Processed  : {stats['page_count']} pages")
            print(f"Extraction Time  : {stats['time_extract']:.2f}s | Compress: {stats['time_compress']:.2f}s | Build: {stats['time_build']:.2f}s")
            print(f"Total Time Taken : {stats['total_time']:.2f} seconds!")
            print(f"Original PDF     : {stats['original_size'] / (1024*1024):.2f} MB")
            print(f"Optimized PDF    : {stats['compressed_size'] / (1024*1024):.2f} MB")
            print(f"Size Reduction   : {stats['size_reduction_pct']:.2f}% CUT!")
            print("=" * 68)
            return
        elif output_ext == '.cbz':
            pages = PDFProcessor.extract_pages_from_pdf(first_input, dpi=args.dpi)
            all_slices = []
            for p in pages:
                if encoder.simd_engine:
                    data, mode = encoder.simd_engine.encode_tile(p)
                elif HAS_OPENCV:
                    _, enc = cv2.imencode(".jpg", p, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    data = enc.tobytes()
                else:
                    from PIL import Image
                    import io
                    pil_img = Image.fromarray(cv2.cvtColor(p, cv2.COLOR_BGR2RGB))
                    buf = io.BytesIO()
                    pil_img.save(buf, format="JPEG", quality=80)
                    data = buf.getvalue()
                all_slices.append({"data": data, "width": p.shape[1], "height": p.shape[0]})
            CBZPackager.create_cbz(args.output, [{"slices": all_slices}])
            orig_sz = os.path.getsize(first_input)
            out_sz = os.path.getsize(args.output)
            print(f"Converted '{first_input}' ({orig_sz/(1024*1024):.1f}MB) -> '{args.output}' ({out_sz/(1024*1024):.1f}MB, Saved {(1-out_sz/max(orig_sz,1))*100:.1f}%)")
            return

    # 5. Handle single archive as input (.cbz or .zip -> .cbz or .pdf)
    if len(args.inputs) == 1 and first_input.lower().endswith(('.cbz', '.zip')) and os.path.isfile(first_input):
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(first_input, 'r') as zf:
                zf.extractall(temp_dir)
            image_paths = []
            for root, _, files in os.walk(temp_dir):
                for f in sorted(files):
                    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp')):
                        image_paths.append(os.path.join(root, f))
            total_orig_bytes = os.path.getsize(first_input)
            t0 = time.time()
            out_sz = process_chapter(image_paths, args.output, encoder, workers=args.workers)
            elapsed = time.time() - t0
            cut_pct = (1.0 - out_sz / max(total_orig_bytes, 1)) * 100
            print(f"Compressed '{first_input}' -> '{args.output}' in {elapsed:.2f}s! ({total_orig_bytes/(1024*1024):.1f}MB -> {out_sz/(1024*1024):.1f}MB, Saved {cut_pct:.1f}%)")
            return

    # 6. Standard collection of files / folder
    image_paths = []
    for inp in args.inputs:
        if os.path.isdir(inp):
            for root, _, files in os.walk(inp):
                for f in sorted(files):
                    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp')):
                        image_paths.append(os.path.join(root, f))
        elif os.path.isfile(inp):
            image_paths.append(inp)

    if not image_paths:
        print("Error: No valid image files found.", file=sys.stderr)
        sys.exit(1)

    image_paths = sorted(image_paths)
    total_original_bytes = sum(os.path.getsize(p) for p in image_paths)

    print("=" * 68)
    print("      FAST MANHWA & COMIC COMPRESSION ENGINE")
    print("=" * 68)
    print(f"Pages to Process : {len(image_paths)} pages")
    print(f"Preset           : {args.preset.upper()}")
    print(f"Total Input Size : {total_original_bytes / (1024*1024):.2f} MB")
    print(f"Parallel Workers : {args.workers} threads")
    print("-" * 68)

    start_time = time.time()
    output_size = process_chapter(image_paths, args.output, encoder, workers=args.workers)

    elapsed = time.time() - start_time
    savings_pct = (1.0 - (output_size / max(total_original_bytes, 1))) * 100
    throughput = (total_original_bytes / (1024 * 1024)) / max(elapsed, 0.001)

    print("-" * 68)
    print("      COMPRESSION COMPLETE")
    print("-" * 68)
    print(f"Time Taken       : {elapsed:.2f} seconds ({len(image_paths)/elapsed:.1f} pages/sec)")
    print(f"Throughput       : {throughput:.2f} MB/sec")
    print(f"Output File      : {args.output}")
    print(f"Output Size      : {output_size / (1024*1024):.2f} MB ({output_size:,} bytes)")
    print(f"Size Reduction   : {savings_pct:.2f}% CUT from original files!")
    print("=" * 68)

if __name__ == "__main__":
    main()
