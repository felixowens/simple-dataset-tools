# Dataset Augmentation Tool Documentation

This Python script augments image/caption datasets by applying various transformations to expand the dataset. Here's documentation on how to use it along with examples.

## Key Features

- Supports multiple augmentation types (flip, rotate, brightness, contrast, blur, color, crop, noise)
- Configurable augmentation parameters
- Parallel processing for faster execution
- Maintains directory structure (optional)
- Generates metadata for tracking augmentations
- Option to augment captions based on image transformations
- Type-safe implementation with robust error handling

## Command Line Usage

```bash
python dataset_augmenter.py --input /path/to/dataset --output /path/to/output [OPTIONS]
```

### Required Arguments

- `--input`, `-i`: Path to input dataset directory or JSON file
- `--output`, `-o`: Path to output directory for augmented dataset

### Optional Arguments

- `--augmentations`, `-a`: Number of augmentations per image (default: 3)
- `--augmentation-types`, `-t`: Types of augmentations to apply (default: FLIP, ROTATE, BRIGHTNESS, CONTRAST, BLUR, COLOR)
- `--maintain-structure`, `-m`: Maintain directory structure in output
- `--caption-augmentation`, `-c`: Augment captions based on image transformations
- `--workers`, `-w`: Number of worker threads (default: 4)
- `--seed`, `-s`: Random seed for reproducibility

## Examples

### Basic Usage

```bash
# Generate 3 augmentations per image using default transformations
python dataset_augmenter.py -i ./my_dataset -o ./augmented_dataset
```

### Advanced Usage

```bash
# Generate 5 augmentations per image with specific transformation types
python dataset_augmenter.py -i ./my_dataset -o ./augmented_dataset \
  -a 5 -t FLIP ROTATE BRIGHTNESS CROP NOISE \
  -m -c -w 8 -s 42
```

## Input Dataset Formats

The script supports two input formats:

### Directory Structure

A folder containing images and corresponding caption text files with the same name:

```txt
dataset/
  ├── image1.jpg
  ├── image1.txt
  ├── subfolder/
  │   ├── image2.png
  │   └── image2.txt
  └── ...
```

### JSON File

A JSON file containing image paths and captions:

```json
[
  {
    "image_path": "/path/to/image1.jpg",
    "caption": "A dog running in a field",
    "metadata": {"optional": "metadata"}
  },
  {
    "image_path": "/path/to/image2.png",
    "caption": "A cat sleeping on a couch"
  }
]
```

## Programmatic Usage

You can also use the library programmatically within your Python code:

```python
from dataset_augmenter import DatasetAugmenter, AugmentationConfig, AugmentationType, DatasetItem
from pathlib import Path

# Create configuration
config = AugmentationConfig(
    enabled_types=[
        AugmentationType.FLIP, 
        AugmentationType.ROTATE,
        AugmentationType.BRIGHTNESS
    ],
    rotation_range=(-45.0, 45.0),  # Custom rotation range
    brightness_range=(0.6, 1.4),   # Custom brightness range
    augmentations_per_image=5       # 5 augmentations per image
)

# Create augmenter
augmenter = DatasetAugmenter(
    config=config,
    output_dir=Path("./augmented_output"),
    maintain_folder_structure=True,
    save_metadata=True,
    num_workers=8
)

# Load dataset (either from directory or manually create the list)
dataset = augmenter.load_dataset(Path("./my_dataset"))

# Alternative: Create dataset manually
# dataset = [
#     DatasetItem(image_path=Path("image1.jpg"), caption="A sunny beach"),
#     DatasetItem(image_path=Path("image2.jpg"), caption="A mountain landscape")
# ]

# Augment dataset
augmented_dataset = augmenter.augment_dataset(dataset)

# Save metadata
augmenter.save_dataset_metadata(augmented_dataset)
```

## Output Format

The script generates:

1. Augmented images with unique filenames
2. Caption text files for each augmented image
3. Metadata files for each augmentation (optional)
4. Overall dataset metadata summary

### Metadata Example

```json
{
  "original_count": 100,
  "augmented_count": 300,
  "total_count": 400,
  "augmentation_stats": {
    "FLIP": 85,
    "ROTATE": 92,
    "BRIGHTNESS": 78,
    "CONTRAST": 0,
    "BLUR": 0,
    "COLOR": 0,
    "CROP": 45,
    "NOISE": 0
  },
  "config": {
    "enabled_types": ["FLIP", "ROTATE", "BRIGHTNESS", "CROP"],
    "augmentations_per_image": 3,
    "caption_augmentation": true,
    "parameters": {
      "rotation_range": [-30.0, 30.0],
      "brightness_range": [0.7, 1.3],
      "contrast_range": [0.7, 1.3],
      "blur_radius_range": [0.5, 1.5],
      "color_factor_range": [0.7, 1.3],
      "crop_percent_range": [0.8, 0.95],
      "noise_factor_range": [5, 20]
    }
  }
}
```

## Dependencies

- Python 3.7+
- PIL/Pillow
- NumPy
- tqdm

Install dependencies using:

```bash
pip install pillow numpy tqdm
```
