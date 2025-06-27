#!/usr/bin/env python3
"""
Annotation Data Manager

Handles loading, saving, and exporting annotations for the image edit prompt dataset.
Compatible with existing JSON format used in the dataset-tools project.
"""

import json
import csv
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class AnnotationDataManager:
    """Manages annotation data with JSON persistence and multiple export formats."""
    
    def __init__(self, dataset_name: Optional[str] = None, data_file: Optional[Path] = None):
        """
        Initialize the data manager.
        
        Args:
            dataset_name: Name of the dataset to manage. If provided, will use dataset-specific storage.
            data_file: Path to the JSON data file. If dataset_name is provided, this is ignored.
        """
        if dataset_name:
            # Use dataset-specific storage
            from dataset_manager import DatasetManager
            dataset_manager = DatasetManager()
            self.data_file = dataset_manager.get_dataset_annotations_path(dataset_name)
            self.dataset_name = dataset_name
            
            if not self.data_file:
                raise ValueError(f"Dataset '{dataset_name}' not found")
        else:
            # Use legacy single-file storage for backward compatibility
            self.data_file = data_file or Path(__file__).parent / 'annotations.json'
            self.dataset_name = None
        
        self.annotations: Dict[str, Dict] = {}
        self._load_data()
    
    def _load_data(self) -> None:
        """Load existing annotations from JSON file."""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.annotations = json.load(f)
                logger.info(f"Loaded {len(self.annotations)} annotations from {self.data_file}")
            except json.JSONDecodeError as e:
                logger.error(f"Error loading annotations: {e}")
                self.annotations = {}
            except Exception as e:
                logger.error(f"Unexpected error loading annotations: {e}")
                self.annotations = {}
        else:
            logger.info("No existing annotations file found, starting fresh")
    
    def _save_data(self) -> None:
        """Save annotations to JSON file."""
        try:
            # Create backup of existing file
            if self.data_file.exists():
                backup_path = self.data_file.with_suffix('.json.backup')
                self.data_file.rename(backup_path)
            
            # Save current data
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.annotations, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self.annotations)} annotations to {self.data_file}")
        except Exception as e:
            logger.error(f"Error saving annotations: {e}")
            raise
    
    def save_annotation(self, before_image: str, after_image: str, 
                       edit_description: str, metadata: Optional[Dict] = None) -> str:
        """
        Save a new annotation.
        
        Args:
            before_image: Filename of the before image
            after_image: Filename of the after image
            edit_description: Description of the edit/transformation
            metadata: Additional metadata dictionary
        
        Returns:
            Unique annotation ID
        """
        annotation_id = str(uuid.uuid4())
        
        annotation = {
            "id": annotation_id,
            "before_image": before_image,
            "after_image": after_image,
            "edit_description": edit_description,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        self.annotations[annotation_id] = annotation
        self._save_data()
        
        return annotation_id
    
    def update_annotation(self, annotation_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing annotation.
        
        Args:
            annotation_id: ID of the annotation to update
            updates: Dictionary of fields to update
        
        Returns:
            True if update successful, False if annotation not found
        """
        if annotation_id not in self.annotations:
            return False
        
        # Update allowed fields
        allowed_fields = ['before_image', 'after_image', 'edit_description', 'metadata']
        for field in allowed_fields:
            if field in updates:
                self.annotations[annotation_id][field] = updates[field]
        
        self.annotations[annotation_id]['updated_at'] = datetime.now().isoformat()
        self._save_data()
        
        return True
    
    def delete_annotation(self, annotation_id: str) -> bool:
        """
        Delete an annotation.
        
        Args:
            annotation_id: ID of the annotation to delete
        
        Returns:
            True if deletion successful, False if annotation not found
        """
        if annotation_id not in self.annotations:
            return False
        
        del self.annotations[annotation_id]
        self._save_data()
        
        return True
    
    def get_annotation(self, annotation_id: str) -> Optional[Dict]:
        """Get a specific annotation by ID."""
        return self.annotations.get(annotation_id)
    
    def get_all_annotations(self) -> Dict[str, Dict]:
        """Get all annotations."""
        return self.annotations.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get annotation statistics."""
        total_annotations = len(self.annotations)
        
        # Count unique images
        before_images = set()
        after_images = set()
        all_images = set()
        
        for annotation in self.annotations.values():
            before_images.add(annotation['before_image'])
            after_images.add(annotation['after_image'])
            all_images.add(annotation['before_image'])
            all_images.add(annotation['after_image'])
        
        return {
            'total_annotations': total_annotations,
            'unique_before_images': len(before_images),
            'unique_after_images': len(after_images),
            'total_unique_images': len(all_images),
            'avg_description_length': self._avg_description_length(),
            'created_at': datetime.now().isoformat()
        }
    
    def _avg_description_length(self) -> float:
        """Calculate average edit description length."""
        if not self.annotations:
            return 0.0
        
        total_length = sum(len(ann['edit_description']) for ann in self.annotations.values())
        return total_length / len(self.annotations)
    
    def export_annotations(self, format_type: str) -> Optional[Path]:
        """
        Export annotations to specified format.
        
        Args:
            format_type: Export format ('json', 'csv', 'jsonl')
        
        Returns:
            Path to exported file, or None if export failed
        """
        export_dir = Path(__file__).parent / 'exports'
        export_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dataset_suffix = f"_{self.dataset_name}" if self.dataset_name else ""
        
        try:
            if format_type == 'json':
                return self._export_json(export_dir, timestamp, dataset_suffix)
            elif format_type == 'csv':
                return self._export_csv(export_dir, timestamp, dataset_suffix)
            elif format_type == 'jsonl':
                return self._export_jsonl(export_dir, timestamp, dataset_suffix)
            else:
                logger.error(f"Unsupported export format: {format_type}")
                return None
        except Exception as e:
            logger.error(f"Error exporting to {format_type}: {e}")
            return None
    
    def _export_json(self, export_dir: Path, timestamp: str, dataset_suffix: str = "") -> Path:
        """Export as JSON file."""
        export_path = export_dir / f'annotations{dataset_suffix}_{timestamp}.json'
        
        # Create export format compatible with existing dataset structure
        export_data = {}
        for ann_id, annotation in self.annotations.items():
            key = f"{annotation['before_image']}_{annotation['after_image']}_{ann_id[:8]}"
            export_data[key] = {
                "before_image": annotation['before_image'],
                "after_image": annotation['after_image'],
                "edit_attributes": {
                    "description": annotation['edit_description'],
                    "metadata": annotation.get('metadata', {}),
                    "created_at": annotation.get('created_at'),
                    "updated_at": annotation.get('updated_at')
                }
            }
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return export_path
    
    def _export_csv(self, export_dir: Path, timestamp: str, dataset_suffix: str = "") -> Path:
        """Export as CSV file."""
        export_path = export_dir / f'annotations{dataset_suffix}_{timestamp}.csv'
        
        with open(export_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                'annotation_id', 'before_image', 'after_image', 'edit_description',
                'created_at', 'updated_at', 'metadata'
            ])
            
            # Write data
            for ann_id, annotation in self.annotations.items():
                writer.writerow([
                    ann_id,
                    annotation['before_image'],
                    annotation['after_image'],
                    annotation['edit_description'],
                    annotation.get('created_at', ''),
                    annotation.get('updated_at', ''),
                    json.dumps(annotation.get('metadata', {}))
                ])
        
        return export_path
    
    def _export_jsonl(self, export_dir: Path, timestamp: str, dataset_suffix: str = "") -> Path:
        """Export as JSONL file (one JSON object per line, useful for ML training)."""
        export_path = export_dir / f'annotations{dataset_suffix}_{timestamp}.jsonl'
        
        with open(export_path, 'w', encoding='utf-8') as f:
            for annotation in self.annotations.values():
                json_line = {
                    "before_image": annotation['before_image'],
                    "after_image": annotation['after_image'],
                    "edit_description": annotation['edit_description'],
                    "metadata": annotation.get('metadata', {})
                }
                f.write(json.dumps(json_line, ensure_ascii=False) + '\n')
        
        return export_path