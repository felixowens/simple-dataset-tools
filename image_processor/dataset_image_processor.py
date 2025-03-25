#!/usr/bin/env python3
"""
Dataset Image Processor

This script processes images in a dataset by converting them to WebP format,
shuffling, renaming, and optionally resizing them.
"""

import os
import argparse
import random
import uuid
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import logging
from typing import List, Tuple, Optional
import math

from PIL import Image
import tqdm


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("DatasetImageProcessor")


class DatasetImageProcessor:
    """Class for processing images in a dataset."""

    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        convert_to_webp: bool = True,
        shuffle: bool = True,
        rename: bool = True,
        resize: bool = False,
        target_megapixels: float = 1.5,
        maintain_folder_structure: bool = False,
        num_workers: int = 4,
        webp_quality: int = 90,
    ):
        """
        Initialize the dataset image processor.

        Args:
            input_dir: Directory containing input images
            output_dir: Directory to save processed images
            convert_to_webp: Whether to convert images to WebP format
            shuffle: Whether to shuffle the order of processing images
            rename: Whether to rename images using UUIDs
            resize: Whether to resize images
            target_megapixels: Target size in megapixels for resizing
            maintain_folder_structure: Whether to maintain folder structure in output
            num_workers: Number of parallel workers for processing
            webp_quality: Quality setting for WebP conversion (0-100)
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.convert_to_webp = convert_to_webp
        self.shuffle = shuffle
        self.rename = rename
        self.resize = resize
        self.target_megapixels = target_megapixels
        self.maintain_folder_structure = maintain_folder_structure
        self.num_workers = num_workers
        self.webp_quality = webp_quality

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Dictionary to track processing statistics
        self.stats = {
            "total_processed": 0,
            "converted_to_webp": 0,
            "resized": 0,
            "renamed": 0,
            "errors": 0,
        }

        # Supported image extensions
        self.supported_extensions = [
            ".jpg",
            ".jpeg",
            ".png",
            ".bmp",
            ".gif",
            ".webp",
            ".tiff",
            ".tif",
        ]

    def get_image_files(self) -> List[Path]:
        """Get all image files from the input directory."""
        image_files = []
        for ext in self.supported_extensions:
            image_files.extend(list(self.input_dir.glob(f"**/*{ext}")))
            image_files.extend(list(self.input_dir.glob(f"**/*{ext.upper()}")))

        return image_files

    def process_images(self) -> None:
        """Process all images in the input directory."""
        image_files = self.get_image_files()
        logger.info(f"Found {len(image_files)} images to process")

        # Shuffle images if requested
        if self.shuffle:
            random.shuffle(image_files)
            logger.info("Images shuffled")

        # Process images in parallel
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            list(
                tqdm.tqdm(
                    executor.map(self._process_image, image_files),
                    total=len(image_files),
                    desc="Processing images",
                )
            )

        logger.info(
            f"Processing complete. Processed {self.stats['total_processed']} images."
        )
        logger.info(f"Converted to WebP: {self.stats['converted_to_webp']}")
        logger.info(f"Resized: {self.stats['resized']}")
        logger.info(f"Renamed: {self.stats['renamed']}")
        logger.info(f"Errors: {self.stats['errors']}")

    def _process_image(self, image_path: Path) -> None:
        """Process a single image."""
        try:
            # Open the image
            image = Image.open(image_path)

            # Determine output path
            if self.maintain_folder_structure:
                rel_path = image_path.relative_to(self.input_dir)
                output_subdir = self.output_dir / rel_path.parent
                output_subdir.mkdir(parents=True, exist_ok=True)

                if self.rename:
                    filename = f"{uuid.uuid4()}"
                    self.stats["renamed"] += 1
                else:
                    filename = image_path.stem
            else:
                output_subdir = self.output_dir

                if self.rename:
                    filename = f"{uuid.uuid4()}"
                    self.stats["renamed"] += 1
                else:
                    filename = image_path.stem

            # Resize if requested
            if self.resize:
                image = self._resize_image(image)
                self.stats["resized"] += 1

            # Determine output format and extension
            if self.convert_to_webp:
                output_ext = ".webp"
                self.stats["converted_to_webp"] += 1
            else:
                output_ext = image_path.suffix

            # Create output path
            output_path = output_subdir / f"{filename}{output_ext}"

            # Save the processed image
            if self.convert_to_webp:
                image.save(output_path, format="WEBP", quality=self.webp_quality)
            else:
                image.save(output_path)

            # Check for caption file and copy it if it exists
            caption_path = image_path.with_suffix(".txt")
            if caption_path.exists():
                output_caption_path = output_path.with_suffix(".txt")
                shutil.copy2(caption_path, output_caption_path)

            self.stats["total_processed"] += 1

        except Exception as e:
            logger.error(f"Error processing {image_path}: {e}")
            self.stats["errors"] += 1

    def _resize_image(self, image: Image.Image) -> Image.Image:
        """Resize an image to the target megapixels while preserving aspect ratio."""
        width, height = image.size
        current_pixels = width * height
        target_pixels = int(self.target_megapixels * 1_000_000)

        if current_pixels <= target_pixels:
            # Image is already smaller than target, no need to resize
            return image

        # Calculate scaling factor
        scale_factor = math.sqrt(target_pixels / current_pixels)

        # Calculate new dimensions
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)

        # Resize the image
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Process images in a dataset")

    parser.add_argument(
        "--input",
        "-i",
        type=str,
        required=True,
        help="Path to input directory containing images",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        required=True,
        help="Path to output directory for processed images",
    )
    parser.add_argument(
        "--no-webp", action="store_true", help="Don't convert images to WebP format"
    )
    parser.add_argument(
        "--no-shuffle",
        action="store_true",
        help="Don't shuffle the order of processing images",
    )
    parser.add_argument(
        "--no-rename", action="store_true", help="Don't rename images using UUIDs"
    )
    parser.add_argument(
        "--resize", action="store_true", help="Resize images to target megapixels"
    )
    parser.add_argument(
        "--megapixels",
        type=float,
        default=1.5,
        help="Target size in megapixels for resizing (default: 1.5)",
    )
    parser.add_argument(
        "--maintain-structure",
        "-m",
        action="store_true",
        help="Maintain directory structure in output",
    )
    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=4,
        help="Number of worker threads (default: 4)",
    )
    parser.add_argument(
        "--webp-quality",
        type=int,
        default=90,
        help="Quality setting for WebP conversion (0-100, default: 90)",
    )

    return parser.parse_args()


def main():
    """
    Main function to run the script.

    Example usage:
    python dataset_image_processor.py --input ./my_dataset --output ./processed_dataset --resize --megapixels 1.5 --workers 8
    """
    args = parse_arguments()

    processor = DatasetImageProcessor(
        input_dir=Path(args.input),
        output_dir=Path(args.output),
        convert_to_webp=not args.no_webp,
        shuffle=not args.no_shuffle,
        rename=not args.no_rename,
        resize=args.resize,
        target_megapixels=args.megapixels,
        maintain_folder_structure=args.maintain_structure,
        num_workers=args.workers,
        webp_quality=args.webp_quality,
    )

    processor.process_images()

    print(
        f"Processing complete! Processed {processor.stats['total_processed']} images, "
        f"with {processor.stats['errors']} errors."
    )


if __name__ == "__main__":
    main()
