import json
import os


class CaptionDataLoader:
    """
    A class to load caption data from various popular formats and a custom JSON format.
    """

    def __init__(self):
        """
        Initializes the CaptionDataLoader.
        """
        self.captions: list[str] = []  # List to store loaded captions

    def load_from_list(self, caption_list):
        """
        Loads captions from a Python list of strings.

        Args:
            caption_list (list of str): A list where each element is a caption string.
        """
        if not isinstance(caption_list, list):
            raise TypeError("Input must be a list of strings.")
        for caption in caption_list:
            if not isinstance(caption, str):
                raise ValueError("List must contain only string captions.")
        self.captions.extend(caption_list)

    def load_from_txt(self, txt_filepath):
        """
        Loads captions from a plain text file, one caption per line.

        Args:
            txt_filepath (str): Path to the text file.
        """
        if not os.path.exists(txt_filepath):
            raise FileNotFoundError(f"Text file not found: {txt_filepath}")
        try:
            with open(txt_filepath, "r", encoding="utf-8") as f:
                for line in f:
                    caption = (
                        line.strip()
                    )  # Remove leading/trailing whitespace, including newlines
                    if caption:  # Ignore empty lines
                        self.captions.append(caption)
        except Exception as e:
            raise RuntimeError(f"Error reading text file: {txt_filepath}. {e}")

    def load_from_json_list(self, json_filepath):
        """
        Loads captions from a JSON file where the root is a list of caption strings.

        Args:
            json_filepath (str): Path to the JSON file.
        """
        if not os.path.exists(json_filepath):
            raise FileNotFoundError(f"JSON file not found: {json_filepath}")
        try:
            with open(json_filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    raise ValueError("JSON file should contain a list at the root.")
                for caption in data:
                    if not isinstance(caption, str):
                        raise ValueError("JSON list must contain only string captions.")
                    self.captions.append(caption)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Error decoding JSON file: {json_filepath}. Invalid JSON format. {e}"
            )
        except Exception as e:
            raise RuntimeError(f"Error reading JSON file: {json_filepath}. {e}")

    def load_from_json_custom(self, json_filepath):
        """
        Loads captions from the custom JSON format.

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
                        )  # or raise an error if strict format is needed
                        continue  # Skip entries that don't match the expected structure
                    caption = value["file_attributes"]["caption"]
                    if isinstance(
                        caption, str
                    ):  # Ensure caption is a string before adding
                        self.captions.append(caption)
                    else:
                        print(
                            f"Warning: Caption for key '{key}' is not a string. Skipping entry."
                        )  # Handle non-string captions as needed
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Error decoding JSON file: {json_filepath}. Invalid JSON format. {e}"
            )
        except Exception as e:
            raise RuntimeError(f"Error reading JSON file: {json_filepath}. {e}")

    def get_captions(self):
        """
        Returns the loaded captions as a list of strings.

        Returns:
            list of str: A list of caption strings.
        """
        return self.captions

    def clear_captions(self):
        """
        Clears any currently loaded captions, resetting to an empty list.
        """
        self.captions = []
