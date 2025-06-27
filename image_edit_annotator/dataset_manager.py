#!/usr/bin/env python3
"""
Dataset Manager

Handles management of multiple datasets for the image edit prompt annotation tool.
Each dataset has its own folder with images and annotations.
"""

import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class DatasetManager:
    """Manages multiple datasets for image edit prompt annotation."""
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize the dataset manager.
        
        Args:
            base_path: Path to the base directory for datasets. Defaults to 'datasets' in current directory.
        """
        self.base_path = base_path or Path(__file__).parent / 'datasets'
        self.base_path.mkdir(exist_ok=True)
        logger.info(f"Dataset manager initialized with base path: {self.base_path}")
    
    def create_dataset(self, name: str, description: str = "", version: str = "1.0") -> Dict[str, Any]:
        """
        Create a new dataset.
        
        Args:
            name: Dataset name (will be used as folder name)
            description: Optional description
            version: Dataset version
            
        Returns:
            Dictionary with dataset information
            
        Raises:
            ValueError: If dataset name already exists or is invalid
        """
        # Validate dataset name
        if not name or not name.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Dataset name must contain only alphanumeric characters, hyphens, and underscores")
        
        dataset_path = self.base_path / name
        
        if dataset_path.exists():
            raise ValueError(f"Dataset '{name}' already exists")
        
        # Create dataset directory structure
        dataset_path.mkdir()
        images_path = dataset_path / 'images'
        images_path.mkdir()
        
        # Create metadata
        metadata = {
            "name": name,
            "description": description,
            "version": version,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "annotation_count": 0,
            "image_count": 0
        }
        
        # Save metadata
        metadata_path = dataset_path / 'metadata.json'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # Create empty annotations file
        annotations_path = dataset_path / 'annotations.json'
        with open(annotations_path, 'w', encoding='utf-8') as f:
            json.dump({}, f, indent=2)
        
        logger.info(f"Created dataset '{name}' at {dataset_path}")
        return metadata
    
    def list_datasets(self) -> List[Dict[str, Any]]:
        """
        List all available datasets.
        
        Returns:
            List of dataset metadata dictionaries
        """
        datasets = []
        
        for dataset_path in self.base_path.iterdir():
            if dataset_path.is_dir():
                try:
                    metadata = self.get_dataset_metadata(dataset_path.name)
                    if metadata:
                        datasets.append(metadata)
                except Exception as e:
                    logger.warning(f"Could not load metadata for dataset {dataset_path.name}: {e}")
        
        # Sort by creation date (newest first)
        datasets.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return datasets
    
    def get_dataset_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific dataset.
        
        Args:
            name: Dataset name
            
        Returns:
            Dataset metadata dictionary or None if not found
        """
        dataset_path = self.base_path / name
        metadata_path = dataset_path / 'metadata.json'
        
        if not metadata_path.exists():
            return None
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Update counts
            metadata['annotation_count'] = self._count_annotations(name)
            metadata['image_count'] = self._count_images(name)
            
            return metadata
        except Exception as e:
            logger.error(f"Error loading metadata for dataset '{name}': {e}")
            return None
    
    def update_dataset_metadata(self, name: str, updates: Dict[str, Any]) -> bool:
        """
        Update dataset metadata.
        
        Args:
            name: Dataset name
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        dataset_path = self.base_path / name
        metadata_path = dataset_path / 'metadata.json'
        
        if not metadata_path.exists():
            return False
        
        try:
            # Load current metadata
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Update allowed fields
            allowed_fields = ['description', 'version']
            for field in allowed_fields:
                if field in updates:
                    metadata[field] = updates[field]
            
            metadata['updated_at'] = datetime.now().isoformat()
            
            # Save updated metadata
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.error(f"Error updating metadata for dataset '{name}': {e}")
            return False
    
    def delete_dataset(self, name: str) -> bool:
        """
        Delete a dataset and all its data.
        
        Args:
            name: Dataset name
            
        Returns:
            True if successful, False otherwise
        """
        dataset_path = self.base_path / name
        
        if not dataset_path.exists():
            return False
        
        try:
            shutil.rmtree(dataset_path)
            logger.info(f"Deleted dataset '{name}'")
            return True
        except Exception as e:
            logger.error(f"Error deleting dataset '{name}': {e}")
            return False
    
    def get_dataset_path(self, name: str) -> Optional[Path]:
        """
        Get the filesystem path for a dataset.
        
        Args:
            name: Dataset name
            
        Returns:
            Path object or None if dataset doesn't exist
        """
        dataset_path = self.base_path / name
        return dataset_path if dataset_path.exists() else None
    
    def get_dataset_images_path(self, name: str) -> Optional[Path]:
        """
        Get the images directory path for a dataset.
        
        Args:
            name: Dataset name
            
        Returns:
            Path object or None if dataset doesn't exist
        """
        dataset_path = self.get_dataset_path(name)
        if dataset_path:
            images_path = dataset_path / 'images'
            images_path.mkdir(exist_ok=True)
            return images_path
        return None
    
    def get_dataset_annotations_path(self, name: str) -> Optional[Path]:
        """
        Get the annotations file path for a dataset.
        
        Args:
            name: Dataset name
            
        Returns:
            Path object or None if dataset doesn't exist
        """
        dataset_path = self.get_dataset_path(name)
        return dataset_path / 'annotations.json' if dataset_path else None
    
    def export_dataset(self, name: str, export_path: Optional[Path] = None) -> Optional[Path]:
        """
        Export a dataset as a ZIP file containing all images and annotations.
        
        Args:
            name: Dataset name
            export_path: Optional path for the export file
            
        Returns:
            Path to the exported ZIP file or None if failed
        """
        dataset_path = self.get_dataset_path(name)
        if not dataset_path:
            return None
        
        if not export_path:
            exports_dir = Path(__file__).parent / 'exports'
            exports_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            export_path = exports_dir / f'dataset_{name}_{timestamp}.zip'
        
        try:
            with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add all files in the dataset directory
                for file_path in dataset_path.rglob('*'):
                    if file_path.is_file():
                        # Store relative path within the ZIP
                        relative_path = file_path.relative_to(dataset_path)
                        zipf.write(file_path, f'{name}/{relative_path}')
            
            logger.info(f"Exported dataset '{name}' to {export_path}")
            return export_path
        except Exception as e:
            logger.error(f"Error exporting dataset '{name}': {e}")
            return None
    
    def import_dataset(self, zip_path: Path, overwrite: bool = False) -> Optional[str]:
        """
        Import a dataset from a ZIP file.
        
        Args:
            zip_path: Path to the ZIP file
            overwrite: Whether to overwrite existing dataset
            
        Returns:
            Dataset name if successful, None otherwise
        """
        if not zip_path.exists():
            return None
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                # Get the dataset name from the ZIP structure
                zip_contents = zipf.namelist()
                if not zip_contents:
                    return None
                
                # Extract dataset name from first entry
                first_entry = zip_contents[0]
                dataset_name = first_entry.split('/')[0]
                
                if not dataset_name:
                    return None
                
                dataset_path = self.base_path / dataset_name
                
                # Check if dataset already exists
                if dataset_path.exists() and not overwrite:
                    raise ValueError(f"Dataset '{dataset_name}' already exists")
                
                # Remove existing dataset if overwriting
                if dataset_path.exists() and overwrite:
                    shutil.rmtree(dataset_path)
                
                # Extract all files
                for file_info in zipf.infolist():
                    if file_info.filename.endswith('/'):
                        continue  # Skip directories
                    
                    # Remove dataset name prefix from path
                    relative_path = '/'.join(file_info.filename.split('/')[1:])
                    if not relative_path:
                        continue
                    
                    target_path = dataset_path / relative_path
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with zipf.open(file_info) as source, open(target_path, 'wb') as target:
                        shutil.copyfileobj(source, target)
                
                logger.info(f"Imported dataset '{dataset_name}' from {zip_path}")
                return dataset_name
        except Exception as e:
            logger.error(f"Error importing dataset from {zip_path}: {e}")
            return None
    
    def _count_annotations(self, name: str) -> int:
        """Count annotations in a dataset."""
        annotations_path = self.get_dataset_annotations_path(name)
        if not annotations_path or not annotations_path.exists():
            return 0
        
        try:
            with open(annotations_path, 'r', encoding='utf-8') as f:
                annotations = json.load(f)
            return len(annotations)
        except Exception:
            return 0
    
    def _count_images(self, name: str) -> int:
        """Count images in a dataset."""
        images_path = self.get_dataset_images_path(name)
        if not images_path:
            return 0
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        count = 0
        
        try:
            for file_path in images_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                    count += 1
        except Exception:
            pass
        
        return count
    
    def get_dataset_statistics(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed statistics for a dataset.
        
        Args:
            name: Dataset name
            
        Returns:
            Statistics dictionary or None if dataset doesn't exist
        """
        if not self.get_dataset_path(name):
            return None
        
        metadata = self.get_dataset_metadata(name)
        if not metadata:
            return None
        
        # Load annotations for more detailed stats
        annotations_path = self.get_dataset_annotations_path(name)
        annotations = {}
        
        if annotations_path and annotations_path.exists():
            try:
                with open(annotations_path, 'r', encoding='utf-8') as f:
                    annotations = json.load(f)
            except Exception:
                pass
        
        # Calculate additional statistics
        total_annotations = len(annotations)
        unique_before_images = set()
        unique_after_images = set()
        
        for annotation in annotations.values():
            unique_before_images.add(annotation.get('before_image', ''))
            unique_after_images.add(annotation.get('after_image', ''))
        
        # Remove empty strings
        unique_before_images.discard('')
        unique_after_images.discard('')
        
        avg_description_length = 0
        if annotations:
            total_length = sum(len(ann.get('edit_description', '')) for ann in annotations.values())
            avg_description_length = total_length / len(annotations)
        
        return {
            'name': name,
            'total_annotations': total_annotations,
            'total_images': metadata['image_count'],
            'unique_before_images': len(unique_before_images),
            'unique_after_images': len(unique_after_images),
            'avg_description_length': round(avg_description_length, 1),
            'created_at': metadata.get('created_at'),
            'updated_at': metadata.get('updated_at'),
            'version': metadata.get('version', '1.0'),
            'description': metadata.get('description', '')
        }