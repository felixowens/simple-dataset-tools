#!/usr/bin/env python3
"""
Image Pair Joiner

This script finds pairs of images in a directory with names in the format <index>a and <index>b,
and joins them horizontally into a single image. It can optionally center crop images before joining.
"""

import os
import argparse
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import logging
from typing import List, Tuple, Dict, Optional

from PIL import Image
import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ImagePairJoiner")


class ImagePairJoiner:
    """Class for joining pairs of images horizontally."""

    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        center_crop: bool = False,
        target_width: Optional[int] = None,
        target_height: Optional[int] = None,
        target_megapixels: Optional[float] = None,
        match_aspect_ratio: bool = True,
        num_workers: int = 4,
        target_aspect_ratio: Optional[Tuple[int, int]] = None,
    ):
        """
        Initialize the image pair joiner.

        Args:
            input_dir: Directory containing input images
            output_dir: Directory to save joined images
            center_crop: Whether to center crop images before joining
            target_width: Target width for each image before joining (if None, uses smaller width)
            target_height: Target height for each image before joining (if None, uses smaller height)
            target_megapixels: Target size in megapixels for resizing images before joining
            match_aspect_ratio: Whether to pad images to match aspect ratios
            num_workers: Number of parallel workers for processing
            target_aspect_ratio: Target aspect ratio as (width, height) tuple (e.g., (2, 3))
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.center_crop = center_crop
        self.target_width = target_width
        self.target_height = target_height
        self.target_megapixels = target_megapixels
        self.match_aspect_ratio = match_aspect_ratio
        self.num_workers = num_workers
        self.target_aspect_ratio = target_aspect_ratio

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Dictionary to track processing statistics
        self.stats = {
            "total_pairs_found": 0,
            "total_processed": 0,
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

    def find_image_pairs(self) -> Dict[str, Tuple[Path, Path]]:
        """Find all image pairs in the input directory."""
        # Get all image files
        image_files = []
        for ext in self.supported_extensions:
            image_files.extend(list(self.input_dir.glob(f"**/*{ext}")))
            image_files.extend(list(self.input_dir.glob(f"**/*{ext.upper()}")))

        # Group images by index
        pairs = {}
        pattern = re.compile(r"(\d+)([ab])\.\w+$")

        for image_path in image_files:
            match = pattern.search(image_path.name)
            if match:
                index, suffix = match.groups()
                if index not in pairs:
                    pairs[index] = {}
                pairs[index][suffix] = image_path

        # Filter out incomplete pairs
        complete_pairs = {}
        for index, pair_dict in pairs.items():
            if "a" in pair_dict and "b" in pair_dict:
                complete_pairs[index] = (pair_dict["a"], pair_dict["b"])

        self.stats["total_pairs_found"] = len(complete_pairs)
        logger.info(f"Found {len(complete_pairs)} image pairs")

        return complete_pairs

    def process_pairs(self) -> None:
        """Process all image pairs in the input directory."""
        pairs = self.find_image_pairs()

        if not pairs:
            logger.warning(
                "No image pairs found. Check naming format (<index>a and <index>b)."
            )
            return

        # Process pairs in parallel
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            list(
                tqdm.tqdm(
                    executor.map(
                        lambda p: self._process_pair(p[0], p[1]), pairs.items()
                    ),
                    total=len(pairs),
                    desc="Joining image pairs",
                )
            )

        logger.info(
            f"Processing complete. Processed {self.stats['total_processed']} image pairs."
        )
        logger.info(f"Errors: {self.stats['errors']}")

    def _process_pair(self, index: str, pair: Tuple[Path, Path]) -> None:
        """Process a single image pair."""
        try:
            image_a_path, image_b_path = pair

            # Open the images
            image_a = Image.open(image_a_path)
            image_b = Image.open(image_b_path)

            # Convert to RGB if needed
            if image_a.mode != "RGB":
                image_a = image_a.convert("RGB")
            if image_b.mode != "RGB":
                image_b = image_b.convert("RGB")

            # Center crop if requested
            if self.center_crop:
                image_a = self._center_crop(image_a)
                image_b = self._center_crop(image_b)

            # Apply target aspect ratio if specified
            if self.target_aspect_ratio:
                image_a = self._apply_aspect_ratio(image_a, self.target_aspect_ratio)
                image_b = self._apply_aspect_ratio(image_b, self.target_aspect_ratio)

            # Resize to target megapixels if specified
            if self.target_megapixels:
                image_a = self._resize_to_megapixels(image_a, self.target_megapixels)
                image_b = self._resize_to_megapixels(image_b, self.target_megapixels)

            # Match aspect ratios if requested
            if self.match_aspect_ratio:
                image_a, image_b = self._match_aspect_ratios(image_a, image_b)

            # Determine the dimensions for the joined image
            if self.target_width and self.target_height:
                # Resize both images to target dimensions
                image_a = self._resize_with_padding(
                    image_a, (self.target_width, self.target_height)
                )
                image_b = self._resize_with_padding(
                    image_b, (self.target_width, self.target_height)
                )
                width_a, height_a = self.target_width, self.target_height
                width_b, height_b = self.target_width, self.target_height
            else:
                # Use the dimensions after previous processing
                width_a, height_a = image_a.size
                width_b, height_b = image_b.size

            # Create a new image with combined width and max height
            max_height = max(height_a, height_b)
            joined_image = Image.new("RGB", (width_a + width_b, max_height))

            # Paste the images side by side, centered vertically if heights differ
            y_offset_a = (max_height - height_a) // 2
            y_offset_b = (max_height - height_b) // 2
            joined_image.paste(image_a, (0, y_offset_a))
            joined_image.paste(image_b, (width_a, y_offset_b))

            # Determine output path
            output_path = self.output_dir / f"{index}_joined.jpg"

            # Save the joined image
            joined_image.save(output_path, format="JPEG", quality=95)

            self.stats["total_processed"] += 1

        except Exception as e:
            logger.error(f"Error processing pair {index}: {e}")
            self.stats["errors"] += 1

    def _center_crop(self, image: Image.Image) -> Image.Image:
        """Center crop an image to make it square."""
        width, height = image.size

        # If already square, return as is
        if width == height:
            return image

        # Determine the crop size (use the smaller dimension)
        crop_size = min(width, height)

        # Calculate crop coordinates
        left = (width - crop_size) // 2
        top = (height - crop_size) // 2
        right = left + crop_size
        bottom = top + crop_size

        # Crop and return
        return image.crop((left, top, right, bottom))

    def _resize_to_megapixels(
        self, image: Image.Image, target_mp: float
    ) -> Image.Image:
        """Resize an image to a target megapixel count while preserving aspect ratio."""
        width, height = image.size
        current_mp = (width * height) / 1_000_000

        if current_mp == 0:
            return image  # Avoid division by zero

        scale_factor = (target_mp / current_mp) ** 0.5

        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)

        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def _match_aspect_ratios(
        self, image_a: Image.Image, image_b: Image.Image
    ) -> Tuple[Image.Image, Image.Image]:
        """
        Match the aspect ratios of two images by padding the image with smaller height.
        The image with larger height is used as reference.
        """
        width_a, height_a = image_a.size
        width_b, height_b = image_b.size

        # If heights are already equal, no need to adjust
        if height_a == height_b:
            return image_a, image_b

        # Determine which image has the larger height to use as reference
        if height_a > height_b:
            # Create a new canvas with height_a and original width_b
            new_image_b = Image.new("RGB", (width_b, height_a), (0, 0, 0))

            # Calculate vertical position to center the original image
            paste_y = (height_a - height_b) // 2

            # Paste original image_b onto the new canvas
            new_image_b.paste(image_b, (0, paste_y))

            return image_a, new_image_b
        else:
            # Create a new canvas with height_b and original width_a
            new_image_a = Image.new("RGB", (width_a, height_b), (0, 0, 0))

            # Calculate vertical position to center the original image
            paste_y = (height_b - height_a) // 2

            # Paste original image_a onto the new canvas
            new_image_a.paste(image_a, (0, paste_y))

            return new_image_a, image_b

    def _resize_with_padding(
        self, image: Image.Image, target_size: Tuple[int, int]
    ) -> Image.Image:
        """Resize an image to a target size with black padding instead of cropping."""
        target_width, target_height = target_size
        return resize_with_padding(image, target_size)

    def _apply_aspect_ratio(
        self, image: Image.Image, aspect_ratio: Tuple[int, int]
    ) -> Image.Image:
        """
        Crop an image to match the target aspect ratio.

        Args:
            image: The input image
            aspect_ratio: Target aspect ratio as (width, height) tuple

        Returns:
            Image cropped to the target aspect ratio
        """
        width, height = image.size
        target_width_ratio, target_height_ratio = aspect_ratio

        # Calculate current aspect ratio
        current_ratio = width / height
        target_ratio = target_width_ratio / target_height_ratio

        if abs(current_ratio - target_ratio) < 0.01:
            # Already very close to target ratio
            return image

        if current_ratio > target_ratio:
            # Image is too wide, crop width
            new_width = int(height * target_ratio)
            left = (width - new_width) // 2
            right = left + new_width
            return image.crop((left, 0, right, height))
        else:
            # Image is too tall, crop height
            new_height = int(width / target_ratio)
            top = (height - new_height) // 2
            bottom = top + new_height
            return image.crop((0, top, width, bottom))


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Join pairs of images horizontally")

    parser.add_argument(
        "--input",
        "-i",
        type=str,
        required=True,
        help="Path to input directory containing image pairs",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        required=True,
        help="Path to output directory for joined images",
    )
    parser.add_argument(
        "--no-crop", action="store_true", help="Don't center crop images before joining"
    )
    parser.add_argument(
        "--width",
        type=int,
        default=None,
        help="Target width for each image before joining",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=None,
        help="Target height for each image before joining",
    )
    parser.add_argument(
        "--megapixels",
        "-mp",
        type=float,
        default=None,
        help="Target megapixels for each image before joining",
    )
    parser.add_argument(
        "--no-match-aspect",
        action="store_true",
        help="Don't match aspect ratios between images",
    )
    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=4,
        help="Number of worker threads (default: 4)",
    )
    parser.add_argument(
        "--aspect-ratio",
        type=str,
        default=None,
        help="Target aspect ratio for each image before joining (format: width:height, e.g., 2:3)",
    )

    return parser.parse_args()


def main():
    """
    Main function to run the script.

    Example usage:
    python image_pair_joiner.py --input ./image_pairs --output ./joined_images --megapixels 1.5 --aspect-ratio 2:3
    """
    args = parse_arguments()

    # Parse aspect ratio if provided
    target_aspect_ratio = None
    if args.aspect_ratio:
        try:
            width_ratio, height_ratio = map(int, args.aspect_ratio.split(":"))
            target_aspect_ratio = (width_ratio, height_ratio)
        except ValueError:
            print(
                f"Invalid aspect ratio format: {args.aspect_ratio}. Using format width:height (e.g., 2:3)"
            )
            exit(1)

    joiner = ImagePairJoiner(
        input_dir=Path(args.input),
        output_dir=Path(args.output),
        center_crop=not args.no_crop,
        target_width=args.width,
        target_height=args.height,
        target_megapixels=args.megapixels,
        match_aspect_ratio=not args.no_match_aspect,
        num_workers=args.workers,
        target_aspect_ratio=target_aspect_ratio,
    )

    joiner.process_pairs()

    print(
        f"Processing complete! Joined {joiner.stats['total_processed']} image pairs, "
        f"with {joiner.stats['errors']} errors."
    )


def resize_with_padding(image, target_size):
    """Resize image to target size with black padding instead of cropping."""
    # Get original dimensions
    original_width, original_height = image.size
    target_width, target_height = target_size

    # Calculate aspect ratios
    original_aspect = original_width / original_height
    target_aspect = target_width / target_height

    # Determine new dimensions while maintaining aspect ratio
    if original_aspect > target_aspect:
        # Image is wider than target
        new_width = target_width
        new_height = int(target_width / original_aspect)
    else:
        # Image is taller than target
        new_height = target_height
        new_width = int(target_height * original_aspect)

    # Resize image while maintaining aspect ratio
    resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Create new black image with target dimensions
    padded_image = Image.new("RGB", target_size, (0, 0, 0))

    # Calculate position to paste resized image (centered)
    paste_x = (target_width - new_width) // 2
    paste_y = (target_height - new_height) // 2

    # Paste resized image onto black background
    padded_image.paste(resized_image, (paste_x, paste_y))

    return padded_image


if __name__ == "__main__":
    main()
