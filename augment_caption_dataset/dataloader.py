import json
import os
from pathlib import Path


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


class CaptionDataLoader:
    """
    A class to load caption data from various popular formats and a custom JSON format.
    """

    def __init__(self, image_base_path: Path, json_base_path: Path):
        """
        Initializes the CaptionDataLoader.
        """
        self.captions: list[str] = []  # List to store loaded captions
        self.items: list[DatasetItem] = []  # List to store loaded items
        self.image_base_path = image_base_path

    def load_from_json_custom(self, json_filepath):
        """
        Loads captions from the custom JSON format.
        Expects the JSON format from VIA JSON export.

        Args:
            json_filepath (str): Path to the JSON file in the custom format.
        """
        if not os.path.exists(json_filepath):
            raise FileNotFoundError(f"JSON file not found: {json_filepath}")
        try:
            with open(json_filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError(
                        "JSON file should contain a dictionary at the root for the custom format."
                    )
                for key, value in data.items():
                    if (
                        not isinstance(value, dict)
                        or "file_attributes" not in value
                        or "caption" not in value["file_attributes"]
                    ):
                        print(
                            f"Warning: Skipping entry with key '{key}' due to unexpected format."
                        )
                        continue
                    caption = value["file_attributes"]["caption"]
                    if isinstance(caption, str):
                        self.captions.append(caption)
                        self.items.append(
                            DatasetItem(
                                key,
                                value["filename"],
                                Path(self.image_base_path, value["filename"]),
                                caption,
                            )
                        )
                    else:
                        print(
                            f"Warning: Caption for key '{key}' is not a string. Skipping entry."
                        )
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Error decoding JSON file: {json_filepath}. Invalid JSON format. {e}"
            )
        except Exception as e:
            raise RuntimeError(f"Error reading JSON file: {json_filepath}. {e}")
