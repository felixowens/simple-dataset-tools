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
        self.dict: dict[str, str] = {}  # Dict to store filename and caption

    def load_from_list(self, caption_list, filenames=None):
        """
        Loads captions from a Python list of strings.

        Args:
            caption_list (list of str): A list where each element is a caption string.
            filenames (list of str, optional): A list of filenames corresponding to the captions.
        """
        if not isinstance(caption_list, list):
            raise TypeError("Input must be a list of strings.")
        for caption in caption_list:
            if not isinstance(caption, str):
                raise ValueError("List must contain only string captions.")

        self.captions.extend(caption_list)

        if filenames:
            if len(filenames) != len(caption_list):
                raise ValueError("Number of filenames must match number of captions")
            for filename, caption in zip(filenames, caption_list):
                self.dict[filename] = caption

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
                for i, line in enumerate(f):
                    caption = line.strip()
                    if caption:  # Ignore empty lines
                        self.captions.append(caption)
                        # Use line number as filename since original filename is unknown
                        self.dict[f"line_{i}"] = caption
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
                for i, caption in enumerate(data):
                    if not isinstance(caption, str):
                        raise ValueError("JSON list must contain only string captions.")
                    self.captions.append(caption)
                    # Use index as filename since original filename is unknown
                    self.dict[f"item_{i}"] = caption
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
                        )
                        continue
                    caption = value["file_attributes"]["caption"]
                    if isinstance(caption, str):
                        self.captions.append(caption)
                        self.dict[key] = caption
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

    def get_captions(self):
        """
        Returns the loaded captions as a list of strings.

        Returns:
            list of str: A list of caption strings.
        """
        return self.captions

    def get_caption_dict(self):
        """
        Returns the dictionary of filename-caption pairs.

        Returns:
            dict: A dictionary mapping filenames to captions.
        """
        return self.dict

    def clear_captions(self):
        """
        Clears any currently loaded captions, resetting to an empty list and dict.
        """
        self.captions = []
        self.dict = {}
