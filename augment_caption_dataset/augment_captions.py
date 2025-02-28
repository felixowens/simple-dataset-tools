#!/usr/bin/env python3
"""
Dataset Augmentation Tool

This script augments a dataset of image/caption pairs by applying various
transformations to expand the dataset to a configurable degree.
"""

import os
import random
import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Callable, Any, Union
import json
from concurrent.futures import ThreadPoolExecutor
import logging
from enum import Enum, auto

import numpy as np
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
import tqdm


class AugmentationType(Enum):
    """Enumeration of supported augmentation types."""

    FLIP = auto()
    ROTATE = auto()
    BRIGHTNESS = auto()
    CONTRAST = auto()
    BLUR = auto()
    COLOR = auto()
    CROP = auto()
    NOISE = auto()


@dataclass
class AugmentationConfig:
    """Configuration for augmentation parameters."""

    enabled_types: List[AugmentationType]
    rotation_range: Tuple[float, float] = (-30.0, 30.0)
    brightness_range: Tuple[float, float] = (0.7, 1.3)
    contrast_range: Tuple[float, float] = (0.7, 1.3)
    blur_radius_range: Tuple[float, float] = (0.5, 1.5)
    color_factor_range: Tuple[float, float] = (0.7, 1.3)
    crop_percent_range: Tuple[float, float] = (0.8, 0.95)
    noise_factor_range: Tuple[float, float] = (5, 20)
    augmentations_per_image: int = 3
    caption_augmentation: bool = False


@dataclass
class DatasetItem:
    """Represents a single item in the dataset."""

    image_path: Path
    caption: str
    metadata: Optional[Dict[str, Any]] = None


class DatasetAugmenter:
    """Class for augmenting image/caption datasets."""

    def __init__(
        self,
        config: AugmentationConfig,
        output_dir: Path,
        maintain_folder_structure: bool = True,
        save_metadata: bool = True,
        num_workers: int = 4,
    ):
        """
        Initialize the dataset augmenter.

        Args:
            config: Configuration for augmentations
            output_dir: Directory to save augmented dataset
            maintain_folder_structure: Whether to maintain folder structure in output
            save_metadata: Whether to save metadata about augmentations
            num_workers: Number of parallel workers for processing
        """
        self.config = config
        self.output_dir = output_dir
        self.maintain_folder_structure = maintain_folder_structure
        self.save_metadata = save_metadata
        self.num_workers = num_workers

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger("DatasetAugmenter")

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Dictionary to track augmentation statistics
        self.stats: Dict[str, int] = {aug_type.name: 0 for aug_type in AugmentationType}
        self.stats["total_original"] = 0
        self.stats["total_augmented"] = 0

    def load_dataset(
        self, dataset_path: Union[Path, List[DatasetItem]]
    ) -> List[DatasetItem]:
        """
        Load dataset from directory or list of items.

        Args:
            dataset_path: Path to dataset directory or list of DatasetItem objects

        Returns:
            List of DatasetItem objects
        """
        if isinstance(dataset_path, list):
            self.logger.info(f"Using provided dataset with {len(dataset_path)} items")
            return dataset_path

        dataset_path = Path(dataset_path)
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset path {dataset_path} does not exist")

        # Check if the path is a JSON file containing dataset information
        if dataset_path.is_file() and dataset_path.suffix.lower() == ".json":
            return self._load_dataset_from_json(dataset_path)

        # Otherwise, assume it's a directory structure with images and captions
        return self._load_dataset_from_directory(dataset_path)

    def _load_dataset_from_json(self, json_path: Path) -> List[DatasetItem]:
        """Load dataset from a JSON file."""
        self.logger.info(f"Loading dataset from JSON: {json_path}")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        items = []
        for item in data:
            # Handle different JSON formats
            if isinstance(item, dict):
                if "image_path" in item and "caption" in item:
                    image_path = Path(item["image_path"])
                    caption = item["caption"]
                    metadata = item.get("metadata")
                    items.append(DatasetItem(image_path, caption, metadata))
                else:
                    self.logger.warning(
                        f"Skipping item with missing required fields: {item}"
                    )
            else:
                self.logger.warning(f"Skipping non-dictionary item: {item}")

        self.logger.info(f"Loaded {len(items)} items from JSON")
        return items

    def _load_dataset_from_directory(self, dir_path: Path) -> List[DatasetItem]:
        """
        Load dataset from a directory structure.

        Assumes images and corresponding caption files with the same name but different extension.
        """
        self.logger.info(f"Loading dataset from directory: {dir_path}")
        items = []

        # Get all image files
        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        image_paths = []

        for ext in image_extensions:
            image_paths.extend(dir_path.glob(f"**/*{ext}"))

        for img_path in image_paths:
            # Look for caption file with the same name but different extension
            caption_path = img_path.with_suffix(".txt")
            if caption_path.exists():
                try:
                    with open(caption_path, "r", encoding="utf-8") as f:
                        caption = f.read().strip()
                    items.append(DatasetItem(img_path, caption))
                except Exception as e:
                    self.logger.warning(f"Error reading caption for {img_path}: {e}")
            else:
                self.logger.warning(f"No caption file found for {img_path}")

        self.logger.info(f"Loaded {len(items)} items from directory")
        return items

    def augment_dataset(self, dataset: List[DatasetItem]) -> List[DatasetItem]:
        """
        Augment the dataset with the configured transformations.

        Args:
            dataset: List of original dataset items

        Returns:
            List of original and augmented dataset items
        """
        self.logger.info(f"Starting augmentation of {len(dataset)} items...")
        self.stats["total_original"] = len(dataset)

        augmented_dataset = dataset.copy()  # Start with the original items

        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            # Process each original item
            future_to_item = {
                executor.submit(self._augment_item, item): item for item in dataset
            }

            # Collect results with progress bar
            for future in tqdm.tqdm(future_to_item, desc="Augmenting dataset"):
                try:
                    new_items = future.result()
                    augmented_dataset.extend(new_items)
                except Exception as e:
                    self.logger.error(f"Error augmenting item: {e}")

        self.stats["total_augmented"] = (
            len(augmented_dataset) - self.stats["total_original"]
        )
        self.logger.info(
            f"Augmentation complete. Created {self.stats['total_augmented']} new items."
        )
        self.logger.info(f"Total dataset size: {len(augmented_dataset)} items")

        # Log augmentation statistics
        for aug_type in AugmentationType:
            self.logger.info(
                f"{aug_type.name} augmentations: {self.stats[aug_type.name]}"
            )

        return augmented_dataset

    def _augment_item(self, item: DatasetItem) -> List[DatasetItem]:
        """Augment a single dataset item with multiple transformations."""
        new_items = []

        try:
            # Load the image
            image = Image.open(item.image_path)

            # Generate n augmented versions
            for i in range(self.config.augmentations_per_image):
                # Choose random augmentation types based on configuration
                available_types = self.config.enabled_types.copy()
                num_augs = min(len(available_types), random.randint(1, 3))
                aug_types = random.sample(available_types, num_augs)

                # Apply the selected augmentations
                aug_image = image.copy()
                aug_meta = {"original_path": str(item.image_path), "augmentations": []}

                for aug_type in aug_types:
                    aug_image, aug_info = self._apply_augmentation(aug_image, aug_type)
                    aug_meta["augmentations"].append(aug_info)
                    self.stats[aug_type.name] += 1

                # Generate augmented caption if enabled
                aug_caption = item.caption
                if self.config.caption_augmentation:
                    aug_caption = self._augment_caption(
                        item.caption, aug_meta["augmentations"]
                    )

                # Create a unique filename for the augmented image
                aug_name = f"{item.image_path.stem}_aug_{i}_{random.randint(1000, 9999)}{item.image_path.suffix}"

                # Determine output path based on configuration
                if self.maintain_folder_structure:
                    rel_path = item.image_path.relative_to(item.image_path.anchor)
                    out_img_path = self.output_dir / rel_path.parent / aug_name
                    out_img_path.parent.mkdir(parents=True, exist_ok=True)
                else:
                    out_img_path = self.output_dir / aug_name

                # Create the new dataset item
                new_item = DatasetItem(
                    image_path=out_img_path,
                    caption=aug_caption,
                    metadata=aug_meta if self.save_metadata else None,
                )

                # Save the augmented image
                aug_image.save(out_img_path)

                # Save caption to file
                caption_path = out_img_path.with_suffix(".txt")
                with open(caption_path, "w", encoding="utf-8") as f:
                    f.write(aug_caption)

                # Save metadata if enabled
                if self.save_metadata:
                    meta_path = out_img_path.with_suffix(".meta.json")
                    with open(meta_path, "w", encoding="utf-8") as f:
                        json.dump(aug_meta, f, indent=2)

                new_items.append(new_item)

        except Exception as e:
            self.logger.error(f"Error processing {item.image_path}: {e}")

        return new_items

    def _apply_augmentation(
        self, image: Image.Image, aug_type: AugmentationType
    ) -> Tuple[Image.Image, Dict[str, Any]]:
        """Apply a specific augmentation to an image and return the result with metadata."""
        aug_info = {"type": aug_type.name}

        if aug_type == AugmentationType.FLIP:
            # Horizontal flip
            image = ImageOps.mirror(image)
            aug_info["direction"] = "horizontal"

        elif aug_type == AugmentationType.ROTATE:
            # Random rotation
            angle = random.uniform(*self.config.rotation_range)
            image = image.rotate(angle, resample=Image.BICUBIC, expand=False)
            aug_info["angle"] = angle

        elif aug_type == AugmentationType.BRIGHTNESS:
            # Adjust brightness
            factor = random.uniform(*self.config.brightness_range)
            image = ImageEnhance.Brightness(image).enhance(factor)
            aug_info["factor"] = factor

        elif aug_type == AugmentationType.CONTRAST:
            # Adjust contrast
            factor = random.uniform(*self.config.contrast_range)
            image = ImageEnhance.Contrast(image).enhance(factor)
            aug_info["factor"] = factor

        elif aug_type == AugmentationType.BLUR:
            # Apply Gaussian blur
            radius = random.uniform(*self.config.blur_radius_range)
            image = image.filter(ImageFilter.GaussianBlur(radius=radius))
            aug_info["radius"] = radius

        elif aug_type == AugmentationType.COLOR:
            # Adjust color saturation
            factor = random.uniform(*self.config.color_factor_range)
            image = ImageEnhance.Color(image).enhance(factor)
            aug_info["factor"] = factor

        elif aug_type == AugmentationType.CROP:
            # Random crop and resize back to original
            original_size = image.size
            crop_percent = random.uniform(*self.config.crop_percent_range)

            width, height = original_size
            new_width = int(width * crop_percent)
            new_height = int(height * crop_percent)

            left = random.randint(0, width - new_width)
            top = random.randint(0, height - new_height)
            right = left + new_width
            bottom = top + new_height

            image = image.crop((left, top, right, bottom))
            image = image.resize(original_size, Image.LANCZOS)

            aug_info.update(
                {"crop_percent": crop_percent, "crop_box": (left, top, right, bottom)}
            )

        elif aug_type == AugmentationType.NOISE:
            # Add random noise
            factor = random.uniform(*self.config.noise_factor_range)
            image = self._add_noise(image, factor)
            aug_info["factor"] = factor

        return image, aug_info

    def _add_noise(self, image: Image.Image, factor: float) -> Image.Image:
        """Add random noise to an image."""
        img_array = np.array(image).astype(np.float32)

        # Generate noise with the same shape as the image
        noise = np.random.normal(0, factor, img_array.shape)

        # Add noise to the image
        noisy_img = img_array + noise

        # Clip values to valid range
        noisy_img = np.clip(noisy_img, 0, 255).astype(np.uint8)

        return Image.fromarray(noisy_img)

    # TODO: need to update this to be more sophisticated, e.g. using a language model
    def _augment_caption(
        self, caption: str, augmentations: List[Dict[str, Any]]
    ) -> str:
        """
        Augment caption based on applied image transformations.

        This is a simple implementation that adds information about transformations.
        A more sophisticated approach would use a language model to rewrite captions.
        """
        aug_desc = []

        for aug in augmentations:
            aug_type = aug["type"]

            if aug_type == AugmentationType.FLIP:
                aug_desc.append("horizontally flipped")
            elif aug_type == AugmentationType.ROTATE:
                ang = aug["angle"]
                direction = "clockwise" if ang > 0 else "counter-clockwise"
                aug_desc.append(f"rotated {abs(ang):.1f}° {direction}")
            elif aug_type == AugmentationType.BRIGHTNESS:
                factor = aug["factor"]
                adj = "brightened" if factor > 1 else "darkened"
                aug_desc.append(adj)
            elif aug_type == AugmentationType.CONTRAST:
                factor = aug["factor"]
                adj = "increased contrast" if factor > 1 else "decreased contrast"
                aug_desc.append(adj)
            elif aug_type == AugmentationType.BLUR:
                aug_desc.append("slightly blurred")
            elif aug_type == AugmentationType.COLOR:
                factor = aug["factor"]
                adj = "increased saturation" if factor > 1 else "decreased saturation"
                aug_desc.append(adj)
            elif aug_type == AugmentationType.CROP:
                aug_desc.append("cropped and resized")
            elif aug_type == AugmentationType.NOISE:
                aug_desc.append("with added noise")

        if aug_desc:
            aug_text = ", ".join(aug_desc)
            return f"{caption} [Image is {aug_text}]"

        return caption

    def save_dataset_metadata(self, dataset: List[DatasetItem]):
        """Save overall dataset metadata to the output directory."""
        metadata = {
            "original_count": self.stats["total_original"],
            "augmented_count": self.stats["total_augmented"],
            "total_count": len(dataset),
            "augmentation_stats": {
                aug_type.name: self.stats[aug_type.name]
                for aug_type in AugmentationType
            },
            "config": {
                "enabled_types": [aug.name for aug in self.config.enabled_types],
                "augmentations_per_image": self.config.augmentations_per_image,
                "caption_augmentation": self.config.caption_augmentation,
                "parameters": {
                    "rotation_range": self.config.rotation_range,
                    "brightness_range": self.config.brightness_range,
                    "contrast_range": self.config.contrast_range,
                    "blur_radius_range": self.config.blur_radius_range,
                    "color_factor_range": self.config.color_factor_range,
                    "crop_percent_range": self.config.crop_percent_range,
                    "noise_factor_range": self.config.noise_factor_range,
                },
            },
        }

        meta_path = self.output_dir / "dataset_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        self.logger.info(f"Dataset metadata saved to {meta_path}")


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Augment an image/caption dataset")

    parser.add_argument(
        "--input",
        "-i",
        type=str,
        required=True,
        help="Path to input dataset directory or JSON file",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        required=True,
        help="Path to output directory for augmented dataset",
    )
    parser.add_argument(
        "--augmentations",
        "-a",
        type=int,
        default=3,
        help="Number of augmentations per image",
    )
    parser.add_argument(
        "--augmentation-types",
        "-t",
        type=str,
        nargs="+",
        default=["FLIP", "ROTATE", "BRIGHTNESS", "CONTRAST", "BLUR", "COLOR"],
        help="Types of augmentations to apply",
    )
    parser.add_argument(
        "--maintain-structure",
        "-m",
        action="store_true",
        help="Maintain directory structure in output",
    )
    parser.add_argument(
        "--caption-augmentation",
        "-c",
        action="store_true",
        help="Augment captions based on image transformations",
    )
    parser.add_argument(
        "--workers", "-w", type=int, default=4, help="Number of worker threads"
    )
    parser.add_argument(
        "--seed", "-s", type=int, default=None, help="Random seed for reproducibility"
    )

    return parser.parse_args()


def main():
    """Main function to run the script."""
    args = parse_arguments()

    # Set random seed if provided
    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)

    # Convert string augmentation types to enum values
    aug_types = []
    for aug_type in args.augmentation_types:
        try:
            aug_types.append(AugmentationType[aug_type])
        except KeyError:
            print(f"Warning: Unknown augmentation type '{aug_type}', skipping")

    # Create augmentation configuration
    config = AugmentationConfig(
        enabled_types=aug_types,
        augmentations_per_image=args.augmentations,
        caption_augmentation=args.caption_augmentation,
    )

    # Create augmenter
    augmenter = DatasetAugmenter(
        config=config,
        output_dir=Path(args.output),
        maintain_folder_structure=args.maintain_structure,
        num_workers=args.workers,
    )

    # Load dataset
    dataset = augmenter.load_dataset(Path(args.input))

    # Augment dataset
    augmented_dataset = augmenter.augment_dataset(dataset)

    # Save dataset metadata
    augmenter.save_dataset_metadata(augmented_dataset)

    print(
        f"Augmentation complete! Original items: {augmenter.stats['total_original']}, "
        f"New items: {augmenter.stats['total_augmented']}, "
        f"Total: {len(augmented_dataset)}"
    )


if __name__ == "__main__":
    main()

    # Example usage:
    # python caption_dataset_augmentation.py -i dataset -o augmented_dataset -a 3 -t FLIP ROTATE BRIGHTNESS CONTRAST BLUR COLOR -m -c -w 4
    # python caption_dataset_augmentation.py -i dataset.json -o augmented_dataset -a 3 -t FLIP ROTATE BRIGHTNESS CONTRAST BLUR COLOR -m -c -w 4
