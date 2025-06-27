#!/usr/bin/env python3
"""
Image Edit Prompt Dataset Annotation Tool - Web Server

A Flask-based web application for annotating image edit prompt datasets.
Allows users to import images, select pairs, and annotate edit descriptions.
"""

import os
import json
import uuid
from pathlib import Path
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_from_directory,
    redirect,
)
from werkzeug.utils import secure_filename
import logging

from data_manager import AnnotationDataManager
from dataset_manager import DatasetManager
from similarity_service import similarity_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["SECRET_KEY"] = "image-edit-annotator-secret-key"
app.config["UPLOAD_FOLDER"] = Path(__file__).parent / "static" / "uploads"
app.config["MAX_CONTENT_LENGTH"] = 1000 * 1024 * 1024  # 100MB max file size

# Allowed image extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "webp"}

# Initialize managers
dataset_manager = DatasetManager()
# data_manager will be initialized per request with dataset context


def allowed_file(filename):
    """Check if file has allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_dataset_from_request() -> str:
    """Get dataset name from request headers or parameters."""
    # Check headers first
    dataset_name = request.headers.get("X-Dataset-Name")

    # Check URL parameters
    if not dataset_name:
        dataset_name = request.args.get("dataset")

    # Check JSON body for POST requests
    if not dataset_name and request.is_json:
        data = request.get_json()
        if data:
            dataset_name = data.get("dataset")

    return dataset_name


def get_data_manager(dataset_name: str = None) -> AnnotationDataManager:
    """Get data manager for specified dataset or default."""
    if dataset_name:
        return AnnotationDataManager(dataset_name=dataset_name)
    else:
        # Fallback to legacy single-file storage
        return AnnotationDataManager()


def get_upload_folder(dataset_name: str = None) -> Path:
    """Get upload folder for specified dataset or default."""
    if dataset_name:
        images_path = dataset_manager.get_dataset_images_path(dataset_name)
        if images_path:
            return images_path

    # Fallback to default upload folder
    return app.config["UPLOAD_FOLDER"]


@app.route("/")
def index():
    """Main annotation interface."""
    # Check if dataset is specified
    dataset_name = request.args.get("dataset")
    if not dataset_name:
        # Redirect to dataset selection
        return redirect("/datasets")

    # Verify dataset exists
    if not dataset_manager.get_dataset_metadata(dataset_name):
        return redirect("/datasets?error=dataset_not_found")

    return render_template("index.html", dataset_name=dataset_name)


@app.route("/datasets")
def dataset_selection():
    """Dataset selection interface."""
    return render_template("dataset_selection.html")


# Dataset Management Endpoints


@app.route("/api/datasets", methods=["GET"])
def list_datasets():
    """List all available datasets."""
    try:
        datasets = dataset_manager.list_datasets()
        return jsonify({"datasets": datasets})
    except Exception as e:
        logger.error(f"Error listing datasets: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/datasets", methods=["POST"])
def create_dataset():
    """Create a new dataset."""
    try:
        data = request.get_json()
        if not data or "name" not in data:
            return jsonify({"error": "Dataset name is required"}), 400

        name = data["name"]
        description = data.get("description", "")
        version = data.get("version", "1.0")

        dataset_info = dataset_manager.create_dataset(name, description, version)
        return jsonify({"success": True, "dataset": dataset_info})

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating dataset: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/datasets/<dataset_name>", methods=["GET"])
def get_dataset(dataset_name):
    """Get dataset information."""
    try:
        metadata = dataset_manager.get_dataset_metadata(dataset_name)
        if not metadata:
            return jsonify({"error": "Dataset not found"}), 404

        return jsonify({"dataset": metadata})
    except Exception as e:
        logger.error(f"Error getting dataset {dataset_name}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/datasets/<dataset_name>", methods=["PUT"])
def update_dataset(dataset_name):
    """Update dataset metadata."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        success = dataset_manager.update_dataset_metadata(dataset_name, data)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Dataset not found"}), 404

    except Exception as e:
        logger.error(f"Error updating dataset {dataset_name}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/datasets/<dataset_name>", methods=["DELETE"])
def delete_dataset(dataset_name):
    """Delete a dataset."""
    try:
        success = dataset_manager.delete_dataset(dataset_name)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Dataset not found"}), 404

    except Exception as e:
        logger.error(f"Error deleting dataset {dataset_name}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/datasets/<dataset_name>/stats", methods=["GET"])
def get_dataset_stats(dataset_name):
    """Get dataset statistics."""
    try:
        stats = dataset_manager.get_dataset_statistics(dataset_name)
        if not stats:
            return jsonify({"error": "Dataset not found"}), 404

        return jsonify({"stats": stats})
    except Exception as e:
        logger.error(f"Error getting dataset stats for {dataset_name}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/datasets/<dataset_name>/export", methods=["GET"])
def export_dataset(dataset_name):
    """Export complete dataset as ZIP file."""
    try:
        export_path = dataset_manager.export_dataset(dataset_name)
        if not export_path or not export_path.exists():
            return jsonify({"error": "Export failed"}), 500

        return send_from_directory(
            export_path.parent,
            export_path.name,
            as_attachment=True,
            download_name=f"dataset_{dataset_name}.zip",
        )
    except Exception as e:
        logger.error(f"Error exporting dataset {dataset_name}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/datasets/import", methods=["POST"])
def import_dataset():
    """Import dataset from ZIP file."""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        if not file or not file.filename:
            return jsonify({"error": "No file selected"}), 400

        overwrite = request.form.get("overwrite", "false").lower() == "true"

        # Save uploaded file temporarily
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_file:
            file.save(temp_file.name)
            temp_path = Path(temp_file.name)

        try:
            dataset_name = dataset_manager.import_dataset(
                temp_path, overwrite=overwrite
            )
            if dataset_name:
                return jsonify({"success": True, "dataset_name": dataset_name})
            else:
                return jsonify({"error": "Import failed"}), 500
        finally:
            # Clean up temporary file
            temp_path.unlink(missing_ok=True)

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error importing dataset: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/datasets/<dataset_name>/migrate-images", methods=["POST"])
def migrate_dataset_images(dataset_name):
    """Migrate images from legacy uploads to dataset-specific folder."""
    try:
        # Get dataset images directory
        dataset_images_path = dataset_manager.get_dataset_images_path(dataset_name)
        if not dataset_images_path:
            return jsonify({"error": "Dataset not found"}), 404

        # Get legacy uploads directory
        legacy_dir = app.config["UPLOAD_FOLDER"]
        if not legacy_dir.exists():
            return jsonify({"error": "No legacy images found"}), 404

        # Get annotations to see which images are actually used by this dataset
        data_manager = get_data_manager(dataset_name)
        annotations = data_manager.get_all_annotations()

        # Find all image filenames referenced in annotations
        referenced_images = set()
        for annotation in annotations.values():
            referenced_images.add(annotation.get("before_image"))
            referenced_images.add(annotation.get("after_image"))

        # Remove None values
        referenced_images.discard(None)
        referenced_images.discard("")

        migrated_count = 0
        skipped_count = 0

        for image_filename in referenced_images:
            legacy_path = legacy_dir / image_filename
            if legacy_path.exists() and legacy_path.is_file():
                dataset_path = dataset_images_path / image_filename

                # Copy file to dataset directory
                if not dataset_path.exists():
                    import shutil

                    shutil.copy2(legacy_path, dataset_path)
                    migrated_count += 1
                    logger.info(f"Migrated image: {image_filename}")
                else:
                    skipped_count += 1
                    logger.info(f"Skipped existing image: {image_filename}")

        return jsonify(
            {
                "success": True,
                "migrated": migrated_count,
                "skipped": skipped_count,
                "total_referenced": len(referenced_images),
            }
        )

    except Exception as e:
        logger.error(f"Error migrating images for dataset {dataset_name}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/upload", methods=["POST"])
def upload_files():
    """Handle multiple file uploads."""
    if "files" not in request.files:
        return jsonify({"error": "No files provided"}), 400

    # Get dataset context
    dataset_name = get_dataset_from_request()
    upload_folder = get_upload_folder(dataset_name)

    files = request.files.getlist("files")
    uploaded_files = []

    for file in files:
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add UUID to prevent filename conflicts
            name, ext = os.path.splitext(filename)
            unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"

            filepath = upload_folder / unique_filename
            file.save(filepath)

            # Generate appropriate URL based on dataset context
            if dataset_name:
                url = f"/api/datasets/{dataset_name}/images/{unique_filename}"
            else:
                url = f"/static/uploads/{unique_filename}"

            uploaded_files.append(
                {"filename": unique_filename, "original_name": filename, "url": url}
            )

            # Add image to similarity index
            try:
                similarity_service.add_image(unique_filename, filepath)
            except Exception as e:
                logger.warning(f"Failed to add image to similarity index: {e}")

    logger.info(
        f"Uploaded {len(uploaded_files)} files to dataset '{dataset_name or 'default'}'"
    )
    return jsonify({"files": uploaded_files})


@app.route("/api/datasets/<dataset_name>/images/<filename>")
def serve_dataset_image(dataset_name, filename):
    """Serve an image from a specific dataset."""
    try:
        images_path = dataset_manager.get_dataset_images_path(dataset_name)
        if not images_path:
            return jsonify({"error": "Dataset not found"}), 404

        return send_from_directory(images_path, filename)
    except Exception as e:
        logger.error(f"Error serving image {filename} from dataset {dataset_name}: {e}")
        return jsonify({"error": "Image not found"}), 404


@app.route("/api/images")
def get_images():
    """Get list of all uploaded images."""
    # Get dataset context
    dataset_name = get_dataset_from_request()
    upload_dir = get_upload_folder(dataset_name)
    images = []

    logger.info(f"Getting images for dataset: {dataset_name}")
    logger.info(f"Upload directory: {upload_dir}")
    logger.info(f"Upload directory exists: {upload_dir.exists()}")

    # Check dataset-specific directory first
    if upload_dir.exists():
        files_found = list(upload_dir.iterdir())
        logger.info(f"Files in dataset directory: {[f.name for f in files_found]}")

        for file_path in files_found:
            if file_path.is_file() and allowed_file(file_path.name):
                # Generate appropriate URL based on dataset context
                if dataset_name:
                    url = f"/api/datasets/{dataset_name}/images/{file_path.name}"
                else:
                    url = f"/static/uploads/{file_path.name}"

                images.append({"filename": file_path.name, "url": url})
                logger.info(f"Added image from dataset directory: {file_path.name}")

    # If no images found in dataset directory and we have a dataset, check legacy uploads
    if len(images) == 0 and dataset_name:
        legacy_dir = app.config["UPLOAD_FOLDER"]
        logger.info(f"No images in dataset directory, checking legacy: {legacy_dir}")

        if legacy_dir.exists():
            legacy_files = list(legacy_dir.iterdir())
            logger.info(f"Files in legacy directory: {[f.name for f in legacy_files]}")

            for file_path in legacy_files:
                if file_path.is_file() and allowed_file(file_path.name):
                    # Use legacy URL for legacy images
                    images.append(
                        {
                            "filename": file_path.name,
                            "url": f"/static/uploads/{file_path.name}",
                        }
                    )
                    logger.info(f"Added image from legacy directory: {file_path.name}")

    # If no dataset specified, just check legacy directory
    if not dataset_name:
        legacy_dir = app.config["UPLOAD_FOLDER"]
        if legacy_dir.exists():
            for file_path in legacy_dir.iterdir():
                if file_path.is_file() and allowed_file(file_path.name):
                    images.append(
                        {
                            "filename": file_path.name,
                            "url": f"/static/uploads/{file_path.name}",
                        }
                    )

    logger.info(f"Returning {len(images)} images")
    return jsonify({"images": images})


@app.route("/api/images/filtered")
def get_filtered_images():
    """Get filtered list of images based on their usage in annotations."""
    try:
        # Get filter type from query parameters
        filter_type = request.args.get("filter", "all")

        # Get dataset context
        dataset_name = get_dataset_from_request()
        data_manager = get_data_manager(dataset_name)

        # Get all images
        images_response = get_images()
        if images_response.status_code != 200:
            return images_response

        all_images = images_response.get_json()["images"]

        # Get all annotations to determine usage
        annotations = data_manager.get_all_annotations()

        # Build usage sets
        before_images = set()
        after_images = set()

        for annotation in annotations.values():
            before_images.add(annotation.get("before_image"))
            after_images.add(annotation.get("after_image"))

        # Remove None values
        before_images.discard(None)
        before_images.discard("")
        after_images.discard(None)
        after_images.discard("")

        used_images = before_images | after_images

        # Filter images based on type
        if filter_type == "all":
            filtered_images = all_images
        elif filter_type == "unused":
            filtered_images = [
                img for img in all_images if img["filename"] not in used_images
            ]
        elif filter_type == "before-only":
            filtered_images = [
                img
                for img in all_images
                if img["filename"] in before_images
                and img["filename"] not in after_images
            ]
        elif filter_type == "after-only":
            filtered_images = [
                img
                for img in all_images
                if img["filename"] in after_images
                and img["filename"] not in before_images
            ]
        elif filter_type == "used":
            filtered_images = [
                img for img in all_images if img["filename"] in used_images
            ]
        else:
            logger.error(f"Invalid filter type: {filter_type}")
            return jsonify({"error": "Invalid filter type"}), 400

        # Add usage metadata to each image
        for img in filtered_images:
            filename = img["filename"]
            img["usage"] = {
                "used_as_before": filename in before_images,
                "used_as_after": filename in after_images,
                "is_used": filename in used_images,
            }

        return jsonify(
            {
                "images": filtered_images,
                "filter": filter_type,
                "counts": {
                    "total": len(all_images),
                    "filtered": len(filtered_images),
                    "unused": len(
                        [
                            img
                            for img in all_images
                            if img["filename"] not in used_images
                        ]
                    ),
                    "before_only": len(
                        [
                            img
                            for img in all_images
                            if img["filename"] in before_images
                            and img["filename"] not in after_images
                        ]
                    ),
                    "after_only": len(
                        [
                            img
                            for img in all_images
                            if img["filename"] in after_images
                            and img["filename"] not in before_images
                        ]
                    ),
                    "used": len(
                        [img for img in all_images if img["filename"] in used_images]
                    ),
                },
            }
        )

    except Exception as e:
        logger.error(f"Error getting filtered images: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/images/similar/<filename>")
def get_similar_images(filename):
    """Get images similar to the specified image."""
    try:
        # Get dataset context
        dataset_name = get_dataset_from_request()
        upload_dir = app.config["UPLOAD_FOLDER"]

        logger.info(f"Looking for similar images to {filename} in {upload_dir}")

        # Check if target image exists in upload directory
        target_path = upload_dir / filename
        if not target_path.exists():
            logger.error(f"Target image not found: {target_path}")
            return jsonify({"error": "Target image not found"}), 404

        # Rebuild similarity index for current upload directory to ensure all images are indexed
        try:
            indexed_count = similarity_service.rebuild_index(upload_dir)
            logger.info(f"Rebuilt similarity index with {indexed_count} images")
        except Exception as e:
            logger.warning(f"Failed to rebuild similarity index: {e}")

        # Get similarity parameters from query string
        max_results = int(request.args.get("max_results", 15))
        max_similarity = float(request.args.get("max_similarity", 0.5))

        # Ensure the target image is in the similarity index
        if not similarity_service.add_image(filename, target_path):
            logger.error(f"Could not process target image: {filename}")
            return jsonify({"error": "Could not process target image"}), 500

        # Find similar images
        similar_images = similarity_service.find_similar_images(
            filename, max_results=max_results, max_similarity_score=max_similarity
        )

        logger.info(f"Similarity service found {len(similar_images)} similar images")

        # Get all available images to build full image objects
        images_response = get_images()
        if images_response.status_code != 200:
            logger.error("Could not retrieve image list")
            return jsonify({"error": "Could not retrieve image list"}), 500

        all_images = images_response.get_json()["images"]
        image_lookup = {img["filename"]: img for img in all_images}

        # Build response with full image objects and similarity scores
        similar_image_objects = []
        for similar_filename, similarity_score in similar_images:
            if similar_filename in image_lookup:
                image_obj = image_lookup[similar_filename].copy()
                image_obj["similarity_score"] = round(similarity_score, 3)
                similar_image_objects.append(image_obj)

        logger.info(f"Found {len(similar_image_objects)} similar images for {filename}")

        return jsonify(
            {
                "target_image": filename,
                "similar_images": similar_image_objects,
                "total_found": len(similar_image_objects),
                "parameters": {
                    "max_results": max_results,
                    "max_similarity": max_similarity,
                },
            }
        )

    except ValueError as e:
        logger.error(f"Invalid parameter: {e}")
        return jsonify({"error": f"Invalid parameter: {e}"}), 400
    except Exception as e:
        logger.error(f"Error finding similar images for {filename}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/annotations", methods=["GET"])
def get_annotations():
    """Get all annotations."""
    dataset_name = get_dataset_from_request()
    data_manager = get_data_manager(dataset_name)
    return jsonify(data_manager.get_all_annotations())


@app.route("/api/annotations", methods=["POST"])
def save_annotation():
    """Save a new annotation."""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ["before_image", "after_image", "edit_description"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        dataset_name = get_dataset_from_request()
        data_manager = get_data_manager(dataset_name)

        annotation_id = data_manager.save_annotation(
            before_image=data["before_image"],
            after_image=data["after_image"],
            edit_description=data["edit_description"],
            metadata=data.get("metadata", {}),
        )

        return jsonify({"success": True, "annotation_id": annotation_id})

    except Exception as e:
        logger.error(f"Error saving annotation: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/annotations/<annotation_id>", methods=["PUT"])
def update_annotation(annotation_id):
    """Update an existing annotation."""
    try:
        data = request.get_json()
        dataset_name = get_dataset_from_request()
        data_manager = get_data_manager(dataset_name)

        success = data_manager.update_annotation(annotation_id, data)

        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Annotation not found"}), 404

    except Exception as e:
        logger.error(f"Error updating annotation: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/annotations/<annotation_id>", methods=["DELETE"])
def delete_annotation(annotation_id):
    """Delete an annotation."""
    try:
        dataset_name = get_dataset_from_request()
        data_manager = get_data_manager(dataset_name)

        success = data_manager.delete_annotation(annotation_id)

        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Annotation not found"}), 404

    except Exception as e:
        logger.error(f"Error deleting annotation: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/export/<format>")
def export_data(format):
    """Export annotations in specified format."""
    try:
        if format not in ["json", "csv", "jsonl"]:
            return jsonify({"error": "Unsupported export format"}), 400

        dataset_name = get_dataset_from_request()
        data_manager = get_data_manager(dataset_name)

        export_path = data_manager.export_annotations(format)

        if export_path and export_path.exists():
            download_name = f"annotations.{format}"
            if dataset_name:
                download_name = f"{dataset_name}_annotations.{format}"

            return send_from_directory(
                export_path.parent,
                export_path.name,
                as_attachment=True,
                download_name=download_name,
            )
        else:
            return jsonify({"error": "Export failed"}), 500

    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats")
def get_stats():
    """Get annotation statistics."""
    dataset_name = get_dataset_from_request()
    data_manager = get_data_manager(dataset_name)
    stats = data_manager.get_statistics()
    return jsonify(stats)


@app.route("/api/images/<filename>", methods=["DELETE"])
def delete_image(filename):
    """Delete a specific image file."""
    try:
        dataset_name = get_dataset_from_request()
        upload_dir = get_upload_folder(dataset_name)
        data_manager = get_data_manager(dataset_name)

        file_path = upload_dir / filename

        if not file_path.exists():
            return jsonify({"error": "Image not found"}), 404

        # Remove the file
        file_path.unlink()

        # Remove from similarity index
        try:
            similarity_service.remove_image(filename)
        except Exception as e:
            logger.warning(f"Failed to remove image from similarity index: {e}")

        # Also remove any annotations that reference this image
        annotations_to_remove = []
        for ann_id, annotation in data_manager.annotations.items():
            if (
                annotation.get("before_image") == filename
                or annotation.get("after_image") == filename
            ):
                annotations_to_remove.append(ann_id)

        for ann_id in annotations_to_remove:
            data_manager.delete_annotation(ann_id)

        logger.info(
            f"Deleted image {filename} and {len(annotations_to_remove)} related annotations from dataset '{dataset_name or 'default'}'"
        )

        return jsonify(
            {"success": True, "removed_annotations": len(annotations_to_remove)}
        )

    except Exception as e:
        logger.error(f"Error deleting image {filename}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/images/clear", methods=["POST"])
def clear_images():
    """Clear selected images or all images."""
    try:
        data = request.get_json() or {}
        filenames = data.get("filenames", [])
        clear_all = data.get("clear_all", False)

        dataset_name = get_dataset_from_request()
        upload_dir = get_upload_folder(dataset_name)
        data_manager = get_data_manager(dataset_name)

        removed_files = 0
        removed_annotations = 0

        if clear_all:
            # Remove all uploaded files
            if upload_dir.exists():
                for file_path in upload_dir.iterdir():
                    if file_path.is_file() and allowed_file(file_path.name):
                        file_path.unlink()
                        removed_files += 1

                        # Remove from similarity index
                        try:
                            similarity_service.remove_image(file_path.name)
                        except Exception as e:
                            logger.warning(
                                f"Failed to remove {file_path.name} from similarity index: {e}"
                            )

            # Clear all annotations
            removed_annotations = len(data_manager.annotations)
            data_manager.annotations.clear()
            data_manager._save_data()

        else:
            # Remove specific files
            for filename in filenames:
                file_path = upload_dir / filename
                if file_path.exists():
                    file_path.unlink()
                    removed_files += 1

                    # Remove from similarity index
                    try:
                        similarity_service.remove_image(filename)
                    except Exception as e:
                        logger.warning(
                            f"Failed to remove {filename} from similarity index: {e}"
                        )

            # Remove related annotations
            annotations_to_remove = []
            for ann_id, annotation in data_manager.annotations.items():
                if (
                    annotation.get("before_image") in filenames
                    or annotation.get("after_image") in filenames
                ):
                    annotations_to_remove.append(ann_id)

            for ann_id in annotations_to_remove:
                data_manager.delete_annotation(ann_id)

            removed_annotations = len(annotations_to_remove)

        logger.info(
            f"Cleared {removed_files} files and {removed_annotations} annotations from dataset '{dataset_name or 'default'}'"
        )

        return jsonify(
            {
                "success": True,
                "removed_files": removed_files,
                "removed_annotations": removed_annotations,
            }
        )

    except Exception as e:
        logger.error(f"Error clearing images: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Ensure upload directory exists
    app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)

    # Initialize similarity service with existing images
    try:
        upload_dir = app.config["UPLOAD_FOLDER"]
        count = similarity_service.rebuild_index(upload_dir)
        logger.info(f"Initialized similarity service with {count} existing images")
    except Exception as e:
        logger.error(f"Failed to initialize similarity service: {e}")

    # Run the Flask app
    app.run(debug=True, host="0.0.0.0", port=5000)
