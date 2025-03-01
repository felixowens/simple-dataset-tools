"""
Moondream2 Fine-tuned Model
"""

from pathlib import Path
from model import CaptioningModel
from transformers import AutoModelForCausalLM
from PIL import Image


class Moondream2FT(CaptioningModel):
    path = "/home/felix/tools/moondream2/models/saved/moondream_base_finetuned_v1_a2_100.safetensors"
    prompt = "\n\nQuestion: Describe this image.\n\nAnswer:"

    def __init__(self):
        self.model = AutoModelForCausalLM.from_pretrained(
            self.path,
            revision="2025-01-09",
            trust_remote_code=True,
            device_map={"": "cuda"},
        )

    def generate_caption(self, image_path: Path) -> str:
        img = Image.open(image_path)
        encoded_image = self.model.encode_image(img)

        return self.model.query(encoded_image, self.prompt)["answer"]
