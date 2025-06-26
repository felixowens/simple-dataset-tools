import os
import json
import tempfile
from PIL import Image as PILImage
import shutil

from cvat_sdk import make_client
from cvat_sdk.core.proxies.tasks import ResourceType, Task
from ultralytics import YOLO
from cvat_sdk.api_client.models import (
    PatchedLabeledDataRequest,
    LabeledShapeRequest,
    ShapeType,
)

# --- Configuration ---
# get from env
CVAT_URL = os.getenv("CVAT_URL", "http://localhost:8080")
CVAT_USERNAME = os.getenv("CVAT_USERNAME", "admin")
CVAT_PASSWORD = os.getenv("CVAT_PASSWORD", "admin")
TARGET_TASK_ID = int(os.getenv("TARGET_TASK_ID", 1))
PERSON_LABEL_NAME = os.getenv("PERSON_LABEL_NAME", "person")
YOLO_MODEL_NAME = os.getenv("YOLO_MODEL_NAME", "yolov8n.pt")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.25))
# How many frames to process before uploading annotations
SAVE_FREQUENCY = int(os.getenv("SAVE_FREQUENCY", 10))


# --- Helper Functions ---
def yolo_to_cvat_bbox(yolo_bbox, img_width, img_height):
    """Converts YOLO bbox (center_x, center_y, width, height - normalized) to CVAT bbox (xtl, ytl, xbr, ybr - absolute)."""
    x_center, y_center, w, h = yolo_bbox
    xtl = (x_center - w / 2) * img_width
    ytl = (y_center - h / 2) * img_height
    xbr = (x_center + w / 2) * img_width
    ybr = (y_center + h / 2) * img_height
    return [xtl, ytl, xbr, ybr]


def upload_shapes_to_cvat(task, shapes, cvat_label_id):
    """Upload a batch of shapes to CVAT."""
    if not shapes:
        return

    # Convert dictionary shapes to proper model objects
    cvat_shapes = []
    for shape in shapes:

        cvat_shapes.append(
            LabeledShapeRequest(
                type=ShapeType(shape["type"]),
                occluded=shape["occluded"],
                outside=False,
                z_order=shape["z_order"],
                rotation=0.0,
                points=shape["points"],
                frame=shape["frame"],
                label_id=shape["label_id"],
                group=shape["group"],
                source="auto",  # Marking as auto since it comes from YOLO
                attributes=[],
            )
        )

    # Construct the data payload using the proper CVAT model
    annotations_payload = PatchedLabeledDataRequest(
        version=0, tags=[], shapes=cvat_shapes, tracks=[]
    )

    try:
        # Upload annotations
        print(f"Uploading batch of {len(cvat_shapes)} annotations...")
        task.update_annotations(data=annotations_payload)
        print("Batch uploaded successfully!")
    except Exception as e:
        print(f"Error uploading annotations to CVAT: {e}")
        # Save annotations locally if upload fails
        failed_annotations_file = (
            f"cvat_annotations_task_{task.id}_failed_{len(shapes)}.json"
        )
        with open(failed_annotations_file, "w") as f:
            json.dump(annotations_payload.to_dict(), f, indent=2)
        print(f"Failed annotations saved to {failed_annotations_file}")


# --- Main Script ---
if __name__ == "__main__":
    # 1. Initialize YOLO model
    print(f"Loading YOLO model: {YOLO_MODEL_NAME}...")
    try:
        model = YOLO(YOLO_MODEL_NAME)
        print("YOLO model loaded successfully.")
    except Exception as e:
        print(f"Error loading YOLO model: {e}")
        print("Ensure 'ultralytics' is installed and the model name is correct.")
        exit()

    # 2. Connect to CVAT with the new API
    print(f"Connecting to CVAT at {CVAT_URL}...")
    credentials = (CVAT_USERNAME, CVAT_PASSWORD)

    with make_client(host=CVAT_URL, credentials=credentials) as client:
        try:
            # Get the target task
            task = client.tasks.retrieve(TARGET_TASK_ID)
            print(f"Retrieved task: '{task.name}' (ID: {task.id})")

            # Fetch the labels
            task_labels = {label.name: label for label in task.get_labels()}
            if PERSON_LABEL_NAME not in task_labels:
                print(
                    f"Error: Label '{PERSON_LABEL_NAME}' not found in task '{task.name}'."
                )
                print(f"Available labels: {list(task_labels.keys())}")
                print(
                    "Please add the label to your CVAT task before running this script."
                )
                exit()

            cvat_label_id = task_labels[PERSON_LABEL_NAME].id

            # Prepare for annotations
            current_batch_shapes = []
            processed_count = 0
            temp_image_dir = tempfile.mkdtemp()
            print(f"Temporary image directory: {temp_image_dir}")

            try:
                # 3. Iterate through frames (images) in the task
                jobs = task.get_jobs()
                print(f"Processing frames in task '{task.name}'...")

                for job in jobs:
                    # Process each frame in the job
                    for frame_index in range(job.stop_frame - job.start_frame + 1):
                        # Calculate global frame ID
                        frame_id = job.start_frame + frame_index
                        print(f"\nProcessing frame {frame_id} in job {job.id}")

                        # Download the frame
                        try:
                            # Download the frame using the API
                            raw_io_base = job.get_frame(frame_index, quality="original")

                            # Create a file path for the image
                            image_path = os.path.join(
                                temp_image_dir, f"frame_{frame_id}.jpg"
                            )

                            # Save the raw IO data to a file
                            with open(image_path, "wb") as f:
                                f.write(raw_io_base.read())

                            if not os.path.exists(image_path):
                                print(f"  Failed to download frame {frame_id}.")
                                continue

                            print(f"  Downloaded frame to {image_path}")

                        except Exception as e:
                            print(f"  Error downloading frame {frame_id}: {e}")
                            continue

                        # 4. Perform YOLO detection
                        try:
                            pil_img = PILImage.open(image_path)
                            img_width, img_height = pil_img.size
                            results = model.predict(source=image_path, verbose=False)
                        except Exception as e:
                            print(
                                f"  Error performing YOLO detection on {image_path}: {e}"
                            )
                            os.remove(image_path)  # Clean up downloaded image
                            continue

                        # 5. Convert detections to CVAT format
                        if results and results[0].boxes:
                            for box in results[0].boxes:
                                class_id = int(box.cls)
                                class_name = model.names[class_id]
                                confidence = float(box.conf)

                                if (
                                    class_name.lower() == "person"
                                    and confidence >= CONFIDENCE_THRESHOLD
                                ):
                                    norm_xyxy = box.xyxyn[0].tolist()
                                    xtl = norm_xyxy[0] * img_width
                                    ytl = norm_xyxy[1] * img_height
                                    xbr = norm_xyxy[2] * img_width
                                    ybr = norm_xyxy[3] * img_height

                                    cvat_shape = {
                                        "type": "rectangle",
                                        "label_id": cvat_label_id,
                                        "frame": frame_id,
                                        "points": [xtl, ytl, xbr, ybr],
                                        "occluded": False,
                                        "z_order": 0,
                                        "group": 0,
                                        "attributes": [],
                                    }
                                    current_batch_shapes.append(cvat_shape)
                                    print(
                                        f"    Detected '{PERSON_LABEL_NAME}' (Conf: {confidence:.2f}) at [{xtl:.1f},{ytl:.1f},{xbr:.1f},{ybr:.1f}]"
                                    )
                        else:
                            print(
                                f"  No detections or no 'person' found in frame {frame_id}."
                            )

                        # Clean up downloaded image for this frame
                        os.remove(image_path)

                        # Increment processed count
                        processed_count += 1

                        # 6. Upload annotations in batches as we go
                        if processed_count % SAVE_FREQUENCY == 0 or (
                            job.id == jobs[-1].id
                            and frame_index == (job.stop_frame - job.start_frame)
                        ):
                            upload_shapes_to_cvat(
                                task, current_batch_shapes, cvat_label_id
                            )
                            print(
                                f"Saved annotations after processing {processed_count} frames"
                            )
                            current_batch_shapes = []  # Reset batch after upload

                # Upload any remaining shapes
                if current_batch_shapes:
                    upload_shapes_to_cvat(task, current_batch_shapes, cvat_label_id)
                    print("Uploaded final batch of annotations")

                print(f"\nTotal frames processed: {processed_count}")
                print(f"Check your task in CVAT: {CVAT_URL}/tasks/{TARGET_TASK_ID}")

            finally:
                # Clean up temporary image directory
                print(f"Removing temporary image directory: {temp_image_dir}")
                shutil.rmtree(temp_image_dir)

        except Exception as e:
            print(f"Error accessing CVAT task: {e}")
            exit()

    print("\nScript finished.")
