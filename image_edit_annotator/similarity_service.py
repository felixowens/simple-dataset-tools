#!/usr/bin/env python3
"""
Image Similarity Service

Provides image similarity functionality using perceptual hashing.
Computes and compares perceptual hashes to find similar images.
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import imagehash
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


class ImageSimilarityService:
    """Service for computing and comparing image similarity using perceptual hashing."""
    
    def __init__(self):
        self._hash_cache: Dict[str, str] = {}  # filename -> hash string
        self._image_paths: Dict[str, Path] = {}  # filename -> full path
        
    def compute_hash(self, image_path: Path) -> Optional[str]:
        """Compute perceptual hash for an image."""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Compute perceptual hash
                hash_value = imagehash.phash(img, hash_size=8)
                return str(hash_value)
        except Exception as e:
            logger.error(f"Error computing hash for {image_path}: {e}")
            return None
    
    def add_image(self, filename: str, image_path: Path) -> bool:
        """Add an image to the similarity index."""
        try:
            if not image_path.exists():
                logger.warning(f"Image path does not exist: {image_path}")
                return False
            
            hash_value = self.compute_hash(image_path)
            if hash_value:
                self._hash_cache[filename] = hash_value
                self._image_paths[filename] = image_path
                logger.info(f"Added image to similarity index: {filename}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding image {filename}: {e}")
            return False
    
    def remove_image(self, filename: str) -> bool:
        """Remove an image from the similarity index."""
        try:
            if filename in self._hash_cache:
                del self._hash_cache[filename]
            if filename in self._image_paths:
                del self._image_paths[filename]
            logger.info(f"Removed image from similarity index: {filename}")
            return True
        except Exception as e:
            logger.error(f"Error removing image {filename}: {e}")
            return False
    
    def compute_similarity_score(self, hash1: str, hash2: str) -> float:
        """Compute similarity score between two hashes (0.0 = identical, 1.0 = completely different)."""
        try:
            # Convert hash strings to imagehash objects
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            
            # Compute Hamming distance
            hamming_distance = h1 - h2
            
            # Normalize to 0-1 scale (64 is max hamming distance for 8x8 hash)
            similarity_score = hamming_distance / 64.0
            return similarity_score
        except Exception as e:
            logger.error(f"Error computing similarity score: {e}")
            return 1.0  # Return max distance on error
    
    def find_similar_images(self, target_filename: str, max_results: int = 15, 
                          max_similarity_score: float = 0.5) -> List[Tuple[str, float]]:
        """
        Find images similar to the target image.
        
        Args:
            target_filename: The filename to find similar images for
            max_results: Maximum number of results to return
            max_similarity_score: Maximum similarity score to include (0.0 = identical, 1.0 = completely different)
        
        Returns:
            List of (filename, similarity_score) tuples, sorted by similarity (most similar first)
        """
        if target_filename not in self._hash_cache:
            logger.warning(f"Target image not in cache: {target_filename}")
            return []
        
        target_hash = self._hash_cache[target_filename]
        similarities = []
        
        try:
            for filename, hash_value in self._hash_cache.items():
                # Skip the target image itself
                if filename == target_filename:
                    continue
                
                # Compute similarity score
                score = self.compute_similarity_score(target_hash, hash_value)
                
                # Only include if similarity is below threshold
                if score <= max_similarity_score:
                    similarities.append((filename, score))
            
            # Sort by similarity score (most similar first)
            similarities.sort(key=lambda x: x[1])
            
            # Limit results
            similarities = similarities[:max_results]
            
            logger.info(f"Found {len(similarities)} similar images for {target_filename}")
            return similarities
            
        except Exception as e:
            logger.error(f"Error finding similar images for {target_filename}: {e}")
            return []
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about the similarity index."""
        return {
            'total_images': len(self._hash_cache),
            'total_hashes': len(self._hash_cache),
            'total_paths': len(self._image_paths)
        }
    
    def rebuild_index(self, image_directory: Path) -> int:
        """Rebuild the entire similarity index from an image directory."""
        logger.info(f"Rebuilding similarity index from {image_directory}")
        
        # Clear existing cache
        self._hash_cache.clear()
        self._image_paths.clear()
        
        # Supported image extensions
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        
        added_count = 0
        
        try:
            if image_directory.exists():
                for image_path in image_directory.iterdir():
                    if image_path.is_file() and image_path.suffix.lower() in image_extensions:
                        if self.add_image(image_path.name, image_path):
                            added_count += 1
        except Exception as e:
            logger.error(f"Error rebuilding index: {e}")
        
        logger.info(f"Rebuilt similarity index with {added_count} images")
        return added_count
    
    def clear_cache(self) -> None:
        """Clear the entire similarity cache."""
        self._hash_cache.clear()
        self._image_paths.clear()
        logger.info("Cleared similarity cache")


# Global instance
similarity_service = ImageSimilarityService()