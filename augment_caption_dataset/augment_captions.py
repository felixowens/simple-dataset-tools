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
from PIL import Image, ImageEnhance, ImageOps, ImageFilter, ImageDraw
import tqdm

from dataloader import CaptionDataLoader


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
    PATCH_DELETION = auto()


@dataclass
class AugmentationConfig:
    """Configuration for augmentation parameters."""

    # Default values are moderate to avoid drastic changes
    enabled_types: List[AugmentationType]
    rotation_range: Tuple[float, float] = (-10.0, 10.0)
    brightness_range: Tuple[float, float] = (0.9, 1.1)
    contrast_range: Tuple[float, float] = (0.9, 1.1)
    blur_radius_range: Tuple[float, float] = (0.5, 1.5)
    color_factor_range: Tuple[float, float] = (0.7, 1.3)
    crop_percent_range: Tuple[float, float] = (0.8, 0.95)
    noise_factor_range: Tuple[float, float] = (5, 20)
    # TODO: Make more sophisticated, e.g. if caption contains "long shot", reduce patch size by 50%
    patch_size_range: Tuple[float, float] = (0.01, 0.05)
    num_patches_range: Tuple[int, int] = (1, 3)
    patch_fill_color: Tuple[int, int, int] = (0, 0, 0)
    augmentations_per_image: int = 2
    caption_augmentation: bool = False
    seed: Optional[int] = 16


@dataclass
class DatasetItem:
    """
    A class to store a dataset item with an image path, caption, and metadata.
    """

    def __init__(
        self,
        key: str,
        filename: str,
        image_path: Path,
        caption: str,
        metadata: dict | None = None,
    ):
        self.key = key
        self.filename = filename
        self.image_path = image_path
        self.caption = caption
        self.metadata = metadata


class DatasetAugmenter:
    """Class for augmenting image/caption datasets."""

    def __init__(
        self,
        config: AugmentationConfig,
        output_dir: Path,
        maintain_folder_structure: bool = True,
        save_metadata: bool = True,
        num_workers: int = 4,
        copy_originals: bool = True,
    ):
        """
        Initialize the dataset augmenter.

        Args:
            config: Configuration for augmentations
            output_dir: Directory to save augmented dataset
            maintain_folder_structure: Whether to maintain folder structure in output
            save_metadata: Whether to save metadata about augmentations
            num_workers: Number of parallel workers for processing
            copy_originals: Whether to copy original files to output directory
        """
        self.config = config
        self.output_dir = output_dir
        self.maintain_folder_structure = maintain_folder_structure
        self.save_metadata = save_metadata
        self.num_workers = num_workers
        self.copy_originals = copy_originals

        # Set random seed if provided
        if self.config.seed is not None:
            random.seed(self.config.seed)
            np.random.seed(self.config.seed)
            self.logger.info(f"Random seed set to {self.config.seed}")

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
    ) -> list[DatasetItem]:
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

        test_path = "/home/felix/datasets/SCL-caption-tiny/images"

        # Load from dataloader
        data_loader = CaptionDataLoader(Path(test_path), dataset_path)
        data_loader.load_from_json_custom(dataset_path)
        return data_loader.items  # type: ignore

    def augment_dataset(self, dataset: list[DatasetItem]) -> list[DatasetItem]:
        """
        Augment the dataset with the configured transformations.

        Args:
            dataset: List of original dataset items

        Returns:
            List of original and augmented dataset items
        """
        self.logger.info(f"Starting augmentation of {len(dataset)} items...")
        self.stats["total_original"] = len(dataset)

        augmented_dataset = []

        # Copy original items if configured to do so
        if self.copy_originals:
            self.logger.info("Copying original items to output directory...")
            with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                list(
                    tqdm.tqdm(
                        executor.map(self._copy_original_item, dataset),
                        total=len(dataset),
                        desc="Copying original items",
                    )
                )
            augmented_dataset.extend(dataset)
        else:
            augmented_dataset = dataset.copy()

        self.logger.info("Generating augmented items...")
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

    def _copy_original_item(self, item: DatasetItem) -> None:
        """Copy an original dataset item to the output directory."""
        try:
            # Store the original image path
            original_image_path = item.image_path

            # Determine output path based on configuration
            if self.maintain_folder_structure:
                rel_path = original_image_path.relative_to(original_image_path.anchor)
                out_img_path = self.output_dir / rel_path
                out_img_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                out_img_path = self.output_dir / original_image_path.name

            # Copy the image file
            Image.open(original_image_path).save(out_img_path)

            # Save caption to file
            caption_path = out_img_path.with_suffix(".txt")
            with open(caption_path, "w", encoding="utf-8") as f:
                f.write(item.caption)

            # Update the item's image path to point to the new location
            item.image_path = out_img_path

        except Exception as e:
            self.logger.error(f"Error copying original item {item.image_path}: {e}")

    def _augment_item(self, item: DatasetItem) -> list[DatasetItem]:
        """Augment a single dataset item with multiple transformations."""
        new_items = []

        try:
            # Load the image
            image = Image.open(item.image_path)

            # Generate n augmented versions
            for i in range(self.config.augmentations_per_image - 1):
                # Choose random augmentation types based on configuration
                available_types = self.config.enabled_types.copy()
                num_augs = len(available_types)
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
                    key=f"{item.key}_aug_{i}_{random.randint(1000, 9999)}",
                    filename=aug_name,
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

                new_items.append(new_item)

        except Exception as e:
            self.logger.error(f"Error processing {item.image_path}: {e}")

        return new_items

    def _apply_augmentation(
        self, image: Image.Image, aug_type: AugmentationType
    ) -> Tuple[Image.Image, Dict[str, Any]]:
        """Apply a specific augmentation to an image and return the result with metadata."""
        aug_info: dict[str, Any] = {"type": aug_type.name}

        if aug_type == AugmentationType.FLIP:
            # Horizontal flip
            image = ImageOps.mirror(image)
            aug_info["direction"] = "horizontal"

        elif aug_type == AugmentationType.ROTATE:
            # Random rotation
            angle = random.uniform(*self.config.rotation_range)
            image = image.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False)
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
            image = image.resize(original_size, Image.Resampling.LANCZOS)

            aug_info.update(
                {"crop_percent": crop_percent, "crop_box": (left, top, right, bottom)}
            )

        elif aug_type == AugmentationType.NOISE:
            # Add random noise
            factor = random.uniform(*self.config.noise_factor_range)
            image = self._add_noise(image, factor)
            aug_info["factor"] = factor

        elif aug_type == AugmentationType.PATCH_DELETION:
            # Delete random patches from the image
            num_patches = random.randint(*self.config.num_patches_range)
            patches_info = []

            # Create a copy of the image to draw on
            img_draw = image.copy()
            img_width, img_height = img_draw.size

            for _ in range(num_patches):
                # Determine patch size as fraction of image dimensions
                patch_size_factor = random.uniform(*self.config.patch_size_range)
                patch_width = int(img_width * patch_size_factor)
                patch_height = int(img_height * patch_size_factor)

                # Random position for the patch
                left = random.randint(0, img_width - patch_width)
                top = random.randint(0, img_height - patch_height)
                right = left + patch_width
                bottom = top + patch_height

                # Create a patch with the fill color
                draw = ImageDraw.Draw(img_draw)
                draw.rectangle(
                    [left, top, right, bottom], fill=self.config.patch_fill_color
                )

                # Record patch information
                patches_info.append(
                    {
                        "position": (left, top, right, bottom),
                        "size_factor": patch_size_factor,
                    }
                )

            image = img_draw
            aug_info["patches"] = patches_info
            aug_info["num_patches"] = num_patches

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

    def save_dataset_metadata(self, dataset: list[DatasetItem]):
        """Save overall dataset metadata to the output directory."""
        # Save standard metadata
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
                "seed": self.config.seed,
                "parameters": {
                    "rotation_range": self.config.rotation_range,
                    "brightness_range": self.config.brightness_range,
                    "contrast_range": self.config.contrast_range,
                    "blur_radius_range": self.config.blur_radius_range,
                    "color_factor_range": self.config.color_factor_range,
                    "crop_percent_range": self.config.crop_percent_range,
                    "noise_factor_range": self.config.noise_factor_range,
                    "patch_size_range": self.config.patch_size_range,
                    "num_patches_range": self.config.num_patches_range,
                    "patch_fill_color": self.config.patch_fill_color,
                },
            },
        }

        meta_path = self.output_dir / "dataset_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        # Save dataset in the requested JSON format
        dataset_json = {}
        for item in dataset:
            dataset_json[item.key] = {
                "filename": item.filename,
                "file_attributes": {"caption": item.caption},
            }

            # Add metadata if available
            if item.metadata:
                dataset_json[item.key]["file_attributes"]["metadata"] = item.metadata

        dataset_path = self.output_dir / "dataset.json"
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset_json, f, indent=2)

        self.logger.info(f"Dataset metadata saved to {meta_path}")
        self.logger.info(f"Dataset JSON saved to {dataset_path}")


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
        default=["ROTATE", "BRIGHTNESS", "CONTRAST", "PATCH_DELETION"],
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
    parser.add_argument(
        "--skip-originals",
        action="store_true",
        help="Skip copying original files to output directory",
    )
    parser.add_argument(
        "--patch-size",
        type=str,
        default="0.1,0.3",
        help="Range of patch sizes as fraction of image (min,max)",
    )
    parser.add_argument(
        "--num-patches",
        type=str,
        default="1,3",
        help="Range of number of patches to delete (min,max)",
    )
    parser.add_argument(
        "--patch-color",
        type=str,
        default="0,0,0",
        help="RGB color to fill deleted patches (r,g,b)",
    )

    return parser.parse_args()


def main():
    """Main function to run the script."""
    args = parse_arguments()

    # Convert string augmentation types to enum values
    aug_types = []
    for aug_type in args.augmentation_types:
        try:
            aug_types.append(AugmentationType[aug_type])
        except KeyError:
            print(f"Warning: Unknown augmentation type '{aug_type}', skipping")

    # Parse patch deletion parameters
    patch_size_range: Tuple[float, float] = tuple(map(float, args.patch_size.split(",")))  # type: ignore
    num_patches_range: Tuple[int, int] = tuple(map(int, args.num_patches.split(",")))  # type: ignore
    patch_fill_color: Tuple[int, int, int] = tuple(map(int, args.patch_color.split(",")))  # type: ignore

    # Create augmentation configuration
    config = AugmentationConfig(
        enabled_types=aug_types,
        augmentations_per_image=args.augmentations,
        caption_augmentation=args.caption_augmentation,
        patch_size_range=patch_size_range,
        num_patches_range=num_patches_range,
        patch_fill_color=patch_fill_color,
        seed=args.seed,
    )

    # Create augmenter
    augmenter = DatasetAugmenter(
        config=config,
        output_dir=Path(args.output),
        maintain_folder_structure=args.maintain_structure,
        num_workers=args.workers,
        copy_originals=not args.skip_originals,
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
    # python augment_captions.py -i dataset -o augmented_dataset -a 3 -t FLIP ROTATE BRIGHTNESS CONTRAST BLUR COLOR PATCH_DELETION -m -c -w 4
    # python augment_captions.py -i dataset.json -o augmented_dataset -a 3 -t FLIP ROTATE BRIGHTNESS CONTRAST BLUR COLOR PATCH_DELETION -m -c -w 4
