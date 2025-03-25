#!/usr/bin/env python3
"""
Dataset Caption Processor

This script processes captions in a dataset by adding prefixes and performing
other text transformations.
"""

import os
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import logging
from typing import List, Optional
import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("DatasetCaptionProcessor")


class DatasetCaptionProcessor:
    """Class for processing captions in a dataset."""

    def __init__(
        self,
        input_dir: Path,
        output_dir: Optional[Path] = None,
        prefix: Optional[str] = None,
        lowercase_first: bool = True,
        num_workers: int = 4,
    ):
        """
        Initialize the dataset caption processor.

        Args:
            input_dir: Directory containing input images and captions
            output_dir: Directory to save processed captions (if None, modifies in place)
            prefix: Prefix to add to each caption
            lowercase_first: Whether to lowercase the first letter after adding prefix
            num_workers: Number of parallel workers for processing
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.prefix = prefix
        self.lowercase_first = lowercase_first
        self.num_workers = num_workers

        # Create output directory if specified and it doesn't exist
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)

        # Dictionary to track processing statistics
        self.stats = {
            "total_processed": 0,
            "prefixed": 0,
            "errors": 0,
        }

    def get_caption_files(self) -> List[Path]:
        """Get all caption files from the input directory."""
        return list(self.input_dir.glob("**/*.txt"))

    def process_captions(self) -> None:
        """Process all captions in the input directory."""
        caption_files = self.get_caption_files()
        logger.info(f"Found {len(caption_files)} caption files to process")

        # Process captions in parallel
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            list(
                tqdm.tqdm(
                    executor.map(self._process_caption, caption_files),
                    total=len(caption_files),
                    desc="Processing captions",
                )
            )

        logger.info(
            f"Processing complete. Processed {self.stats['total_processed']} captions."
        )
        if self.prefix:
            logger.info(f"Added prefix to {self.stats['prefixed']} captions.")
        logger.info(f"Errors: {self.stats['errors']}")

    def _process_caption(self, caption_path: Path) -> None:
        """Process a single caption file."""
        try:
            # Read the caption
            with open(caption_path, "r", encoding="utf-8") as f:
                caption = f.read().strip()

            # Apply transformations
            modified_caption = caption

            # Add prefix if specified
            if self.prefix:
                if modified_caption and self.lowercase_first:
                    # Lowercase the first letter after adding prefix
                    modified_caption = (
                        self.prefix + modified_caption[0].lower() + modified_caption[1:]
                    )
                else:
                    modified_caption = self.prefix + modified_caption
                self.stats["prefixed"] += 1

            # Determine output path
            if self.output_dir:
                rel_path = caption_path.relative_to(self.input_dir)
                output_path = self.output_dir / rel_path
                output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                output_path = caption_path

            # Write the modified caption
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(modified_caption)

            self.stats["total_processed"] += 1

        except Exception as e:
            logger.error(f"Error processing {caption_path}: {e}")
            self.stats["errors"] += 1


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Process captions in a dataset")

    parser.add_argument(
        "--input",
        "-i",
        type=str,
        required=True,
        help="Path to input directory containing images and captions",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Path to output directory for processed captions (if not specified, modifies in place)",
    )
    parser.add_argument(
        "--prefix",
        "-p",
        type=str,
        help="Prefix to add to each caption",
    )
    parser.add_argument(
        "--no-lowercase",
        action="store_true",
        help="Don't lowercase the first letter of the original caption after adding prefix",
    )
    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=4,
        help="Number of worker threads (default: 4)",
    )

    return parser.parse_args()


def main():
    """
    Main function to run the script.

    Example usage:
    python dataset_caption_processor.py --input ./my_dataset --output ./processed_dataset --prefix "A photo of "
    """
    args = parse_arguments()

    processor = DatasetCaptionProcessor(
        input_dir=Path(args.input),
        output_dir=Path(args.output) if args.output else None,
        prefix=args.prefix,
        lowercase_first=not args.no_lowercase,
        num_workers=args.workers,
    )

    processor.process_captions()

    print(
        f"Processing complete! Processed {processor.stats['total_processed']} captions, "
        f"with {processor.stats['errors']} errors."
    )


if __name__ == "__main__":
    main()
