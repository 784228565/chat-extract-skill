#!/usr/bin/env python3
"""Batch OCR for chat screenshots using RapidOCR. Supports single long image or directory of images."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR


def ocr_image_array(img_array, ocr_engine, name=""):
    """OCR a numpy image array."""
    print(f"OCR: {name} ({img_array.shape[1]}x{img_array.shape[0]})")
    result, _ = ocr_engine(img_array)
    texts = [line[1] for line in result] if result else []
    return texts


def split_and_ocr(image_path, ocr_engine, max_height=25000, overlap=200):
    """Split a long image into chunks and OCR each."""
    img = Image.open(image_path)
    width, height = img.size
    print(f"Image size: {width}x{height}")

    if height <= max_height:
        # Small enough, OCR directly
        texts = ocr_image_array(np.array(img), ocr_engine, image_path.name)
        return [{"image": image_path.name, "texts": texts, "full_text": "\n".join(texts)}]

    # Split into chunks
    chunks = []
    y = 0
    chunk_idx = 0
    while y < height:
        y_end = min(y + max_height, height)
        crop = img.crop((0, y, width, y_end))
        arr = np.array(crop)
        texts = ocr_image_array(arr, ocr_engine, f"{image_path.name}_chunk{chunk_idx}")
        chunks.append({
            "image": f"{image_path.name}_chunk{chunk_idx}",
            "texts": texts,
            "full_text": "\n".join(texts),
            "y_start": y,
            "y_end": y_end
        })
        chunk_idx += 1
        y = y_end - overlap if y_end < height else y_end

    # Merge all texts and deduplicate
    all_texts = []
    seen = set()
    for c in chunks:
        for line in c["texts"]:
            if line not in seen:
                seen.add(line)
                all_texts.append(line)

    return [{
        "image": image_path.name,
        "texts": all_texts,
        "full_text": "\n".join(all_texts),
        "chunks": chunks
    }]


def main(input_path, output_file):
    input_path = Path(input_path)
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    ocr = RapidOCR()

    if input_path.is_file():
        results = split_and_ocr(input_path, ocr)
    elif input_path.is_dir():
        # Exclude long screenshots to avoid duplicates with individual frames
        images = sorted([p for p in input_path.glob("*.png") if not p.name.startswith("long_")])
        if not images:
            print(f"No PNG images found in {input_path}")
            sys.exit(1)
        results = []
        for img in images:
            results.extend(split_and_ocr(img, ocr))
    else:
        print(f"Path not found: {input_path}")
        sys.exit(1)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nDone! Processed {len(results)} image(s)")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python batch_ocr.py <input> [output.json]")
        print("")
        print("  input      : PNG image file or directory containing PNG screenshots")
        print("  output.json: Output JSON path (default: input_dir/all_text_raw.json)")
        print("")
        print("Examples:")
        print("  python batch_ocr.py ./screenshots")
        print("  python batch_ocr.py ./long_screenshot.png")
        sys.exit(1)

    input_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else str(Path(input_path).parent / "all_text_raw.json")
    main(input_path, output_file)
