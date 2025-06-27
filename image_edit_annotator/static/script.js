// Image Edit Prompt Annotator - Frontend JavaScript

class ImageEditAnnotator {
    constructor() {
        this.images = [];
        this.annotations = {};
        this.currentAnnotation = null;
        this.selectedBeforeImage = null;
        this.selectedAfterImage = null;
        this.annotationsList = [];
        this.currentAnnotationIndex = -1;
        this.markedForDeletion = new Set();
        this.datasetName = window.DATASET_CONFIG?.datasetName || null;
        this.isSaving = false;
        this.isAutoSaving = false;
        this.currentFilter = 'all';
        this.filterCounts = {};

        this.initializeEventListeners();
        this.loadExistingData();
        this.updateStats();
    }

    initializeEventListeners() {
        // File upload
        const fileInput = document.getElementById('file-input');
        const uploadBtn = document.getElementById('upload-btn');
        const uploadSection = document.querySelector('.upload-section');

        uploadBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => this.handleFileUpload(e));

        // Drag and drop functionality
        uploadSection.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadSection.classList.add('drag-over');
        });

        uploadSection.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadSection.classList.remove('drag-over');
        });

        uploadSection.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadSection.classList.remove('drag-over');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                // Create a fake event object for handleFileUpload
                const fakeEvent = { target: { files: files } };
                this.handleFileUpload(fakeEvent);
            }
        });

        // Form submission
        const form = document.getElementById('annotation-form');
        form.addEventListener('submit', (e) => this.handleFormSubmit(e));

        // Clear form
        document.getElementById('clear-form').addEventListener('click', () => this.clearForm());

        // Delete annotation
        document.getElementById('delete-annotation').addEventListener('click', () => this.deleteCurrentAnnotation());

        // Export buttons
        document.getElementById('export-json').addEventListener('click', () => this.exportData('json'));
        document.getElementById('export-csv').addEventListener('click', () => this.exportData('csv'));
        document.getElementById('export-jsonl').addEventListener('click', () => this.exportData('jsonl'));

        // Export full dataset button (if available)
        const exportDatasetBtn = document.getElementById('export-dataset');
        if (exportDatasetBtn) {
            exportDatasetBtn.addEventListener('click', () => this.exportFullDataset());
        }

        // Gallery management buttons
        document.getElementById('select-all-btn').addEventListener('click', () => this.selectAllImages());
        document.getElementById('clear-selected-btn').addEventListener('click', () => this.clearSelectedImages());
        document.getElementById('clear-all-btn').addEventListener('click', () => this.clearAllImages());

        // Navigation
        document.getElementById('prev-annotation').addEventListener('click', () => this.navigateAnnotation(-1));
        document.getElementById('next-annotation').addEventListener('click', () => this.navigateAnnotation(1));

        // Image filtering
        document.getElementById('image-filter').addEventListener('change', (e) => this.changeFilter(e.target.value));

        // Modal controls
        document.getElementById('close-modal').addEventListener('click', () => this.closeModal());

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));

        // Form input validation
        const descriptionField = document.getElementById('edit-description');
        if (descriptionField) {
            descriptionField.addEventListener('input', () => this.updateSaveButtonState());
        }

        // Auto-save every 2 minutes (less aggressive) - temporarily disabled for debugging
        // setInterval(() => this.autoSave(), 120000);
    }

    getApiHeaders() {
        const headers = {
            'Content-Type': 'application/json'
        };
        if (this.datasetName) {
            headers['X-Dataset-Name'] = this.datasetName;
        }
        return headers;
    }

    getApiUrl(endpoint) {
        if (this.datasetName) {
            const url = new URL(endpoint, window.location.origin);
            url.searchParams.set('dataset', this.datasetName);
            console.log('API URL with dataset:', url.toString());
            return url.toString();
        }
        console.log('API URL without dataset:', endpoint);
        return endpoint;
    }

    async loadExistingData() {
        try {
            console.log('Loading existing data for dataset:', this.datasetName);

            const [imagesResponse, annotationsResponse] = await Promise.all([
                fetch(this.getApiUrl(`/api/images/filtered?filter=${this.currentFilter}`)),
                fetch(this.getApiUrl('/api/annotations'))
            ]);

            console.log('Images response status:', imagesResponse.status);
            console.log('Annotations response status:', annotationsResponse.status);

            if (imagesResponse.ok) {
                const imagesData = await imagesResponse.json();
                this.images = imagesData.images || [];
                this.filterCounts = imagesData.counts || {};
                console.log('Loaded images:', this.images.length, this.images);
                this.updateFilterCount();
                this.renderImageGrid();

                // If we have a current annotation but no images were displayed, try to reload it
                if (this.currentAnnotationIndex >= 0 && this.annotationsList.length > 0) {
                    const currentAnnotationId = this.annotationsList[this.currentAnnotationIndex];
                    if (currentAnnotationId && (!this.selectedBeforeImage || !this.selectedAfterImage)) {
                        console.log('Reloading current annotation after images loaded');
                        this.loadAnnotation(currentAnnotationId);
                    }
                }
            } else {
                console.error('Failed to load images:', imagesResponse.status, await imagesResponse.text());
            }

            if (annotationsResponse.ok) {
                const annotationsData = await annotationsResponse.json();
                this.annotations = annotationsData || {};
                this.annotationsList = Object.keys(this.annotations);
                console.log('Loaded annotations:', this.annotationsList.length, this.annotations);
                this.updateNavigationControls();

                // If we have annotations but no current selection, load the first one
                if (this.annotationsList.length > 0 && this.currentAnnotationIndex === -1) {
                    this.currentAnnotationIndex = 0;
                    this.loadAnnotation(this.annotationsList[0]);
                }
            } else {
                console.error('Failed to load annotations:', annotationsResponse.status, await annotationsResponse.text());
            }

            this.updateStats();
        } catch (error) {
            console.error('Error loading data:', error);
            this.showMessage('Error loading existing data', 'error');
        }
    }

    async handleFileUpload(event) {
        const files = event.target.files;
        if (files.length === 0) return;

        // Validate file types
        const validFiles = Array.from(files).filter(file => {
            const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'];
            return validTypes.includes(file.type);
        });

        if (validFiles.length === 0) {
            this.showMessage('No valid image files selected', 'error');
            return;
        }

        if (validFiles.length < files.length) {
            this.showMessage(`${files.length - validFiles.length} non-image files were skipped`, 'warning');
        }

        const formData = new FormData();
        validFiles.forEach(file => {
            formData.append('files', file);
        });
        if (this.datasetName) {
            formData.append('dataset', this.datasetName);
        }

        this.showProgress(true);
        this.showMessage(`Uploading ${validFiles.length} image${validFiles.length !== 1 ? 's' : ''}...`, 'info');

        // Disable upload button during upload
        const uploadBtn = document.getElementById('upload-btn');
        const originalText = uploadBtn.textContent;
        uploadBtn.disabled = true;
        uploadBtn.textContent = 'Uploading...';

        try {
            // Use XMLHttpRequest for upload progress
            const response = await this.uploadWithProgress(formData);

            if (response.ok) {
                const data = await response.json();
                this.images.push(...data.files);
                this.renderImageGrid();
                this.updateStats();
                this.showMessage(`Successfully uploaded ${data.files.length} image${data.files.length !== 1 ? 's' : ''}`, 'success');
            } else {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || 'Upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
            this.showMessage(`Error uploading images: ${error.message}`, 'error');
        } finally {
            this.showProgress(false);
            uploadBtn.disabled = false;
            uploadBtn.textContent = originalText;
            event.target.value = ''; // Reset file input
        }
    }

    uploadWithProgress(formData) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            // Track upload progress
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    this.updateProgressBar(percentComplete);
                }
            });

            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve({
                        ok: true,
                        json: () => Promise.resolve(JSON.parse(xhr.responseText))
                    });
                } else {
                    reject(new Error(`Upload failed with status ${xhr.status}`));
                }
            });

            xhr.addEventListener('error', () => {
                reject(new Error('Upload failed'));
            });

            xhr.open('POST', '/api/upload');
            xhr.send(formData);
        });
    }

    updateProgressBar(percentage) {
        const progressFill = document.querySelector('.progress-fill');
        if (progressFill) {
            progressFill.style.width = `${percentage}%`;
        }
    }

    renderImageGrid() {
        const grid = document.getElementById('image-grid');
        grid.innerHTML = '';

        this.images.forEach((image, index) => {
            const imageItem = document.createElement('div');
            imageItem.className = 'image-item';
            imageItem.dataset.filename = image.filename;

            // Add delete checkbox
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'delete-checkbox';
            checkbox.checked = this.markedForDeletion.has(image.filename);
            checkbox.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleImageForDeletion(image.filename, checkbox.checked);
            });

            const img = document.createElement('img');
            img.src = image.url;
            img.alt = image.filename;
            img.title = image.original_name || image.filename;

            // Add usage indicator
            if (image.usage) {
                const usageIndicator = document.createElement('div');
                usageIndicator.className = 'usage-indicator';
                if (image.usage.used_as_before && image.usage.used_as_after) {
                    usageIndicator.textContent = 'B+A';
                    usageIndicator.classList.add('both');
                } else if (image.usage.used_as_before) {
                    usageIndicator.textContent = 'B';
                    usageIndicator.classList.add('before');
                } else if (image.usage.used_as_after) {
                    usageIndicator.textContent = 'A';
                    usageIndicator.classList.add('after');
                }
                if (usageIndicator.textContent) {
                    imageItem.appendChild(usageIndicator);
                }
            }

            imageItem.appendChild(checkbox);
            imageItem.appendChild(img);
            imageItem.addEventListener('click', () => this.selectImage(image, imageItem));

            // Apply visual state
            if (this.markedForDeletion.has(image.filename)) {
                imageItem.classList.add('marked-for-deletion');
            }

            grid.appendChild(imageItem);
        });

        this.updateClearButtonStates();
    }

    selectImage(image, element) {
        if (!this.selectedBeforeImage) {
            // Select as before image
            this.clearImageSelections();
            this.selectedBeforeImage = image;
            element.classList.add('before-selected');
            this.displayImage(image, 'before');
            this.showMessage('Selected before image. Now select the after image.', 'info');
        } else if (!this.selectedAfterImage && image.filename !== this.selectedBeforeImage.filename) {
            // Select as after image
            this.selectedAfterImage = image;
            element.classList.add('selected');
            this.displayImage(image, 'after');
            this.enableForm();
            this.updateSaveButtonState();
            this.showMessage('Image pair selected. You can now add an annotation.', 'success');
        } else if (image.filename === this.selectedBeforeImage.filename) {
            // Deselect before image
            this.clearImageSelections();
            this.selectedBeforeImage = null;
            this.clearImageDisplay('before');
            this.disableForm();
            this.showMessage('Before image deselected', 'info');
        } else {
            // Replace selection
            this.clearImageSelections();
            this.selectedBeforeImage = image;
            this.selectedAfterImage = null;
            element.classList.add('before-selected');
            this.displayImage(image, 'before');
            this.clearImageDisplay('after');
            this.disableForm();
            this.showMessage('Selected before image. Now select the after image.', 'info');
        }

        this.updateSaveButtonState();
    }

    clearImageSelections() {
        document.querySelectorAll('.image-item').forEach(item => {
            item.classList.remove('selected', 'before-selected');
        });
    }

    displayImage(image, position) {
        const container = document.getElementById(`${position}-image-container`);
        container.innerHTML = `<img src="${image.url}" alt="${image.filename}" class="fade-in">`;
    }

    clearImageDisplay(position) {
        const container = document.getElementById(`${position}-image-container`);
        container.innerHTML = '<div class="placeholder">Select an image from the gallery</div>';
    }

    enableForm() {
        const form = document.getElementById('annotation-form');
        const inputs = form.querySelectorAll('input, textarea, select');
        inputs.forEach(input => input.disabled = false);
        this.updateSaveButtonState();
    }

    disableForm() {
        const form = document.getElementById('annotation-form');
        const inputs = form.querySelectorAll('input, textarea, select');
        inputs.forEach(input => input.disabled = true);
        this.updateSaveButtonState();
    }

    updateSaveButtonState() {
        const saveBtn = document.getElementById('save-annotation');
        const deleteBtn = document.getElementById('delete-annotation');
        const descriptionElement = document.getElementById('edit-description');

        if (!saveBtn || !descriptionElement) return;

        const description = descriptionElement.value.trim();
        const canSave = this.selectedBeforeImage && this.selectedAfterImage && description.length > 0;
        const hasCurrentAnnotation = this.currentAnnotationIndex >= 0 && this.annotationsList.length > 0;

        saveBtn.disabled = !canSave;
        deleteBtn.disabled = !hasCurrentAnnotation;

        // Update button text based on state
        if (canSave) {
            saveBtn.textContent = 'Save Annotation';
            saveBtn.classList.remove('btn-disabled');
        } else {
            saveBtn.textContent = 'Save Annotation';
            saveBtn.classList.add('btn-disabled');
        }
    }

    async handleFormSubmit(event) {
        event.preventDefault();
        await this.saveAnnotation();
    }

    async saveAnnotation() {
        if (this.isSaving) {
            return; // Prevent concurrent saves
        }

        if (!this.selectedBeforeImage || !this.selectedAfterImage) {
            this.showMessage('Please select both before and after images', 'error');
            return;
        }

        const description = document.getElementById('edit-description').value.trim();
        if (!description) {
            this.showMessage('Please enter an edit description', 'error');
            return;
        }

        const tags = document.getElementById('edit-tags').value;
        const difficulty = document.getElementById('difficulty').value;

        const annotationData = {
            before_image: this.selectedBeforeImage.filename,
            after_image: this.selectedAfterImage.filename,
            edit_description: description,
            metadata: {
                tags: tags.split(',').map(t => t.trim()).filter(t => t),
                difficulty: difficulty || '',
                created_via: 'web_interface'
            }
        };

        if (this.datasetName) {
            annotationData.dataset = this.datasetName;
        }

        this.isSaving = true;
        this.setSaveStatus('saving');

        try {
            const response = await fetch('/api/annotations', {
                method: 'POST',
                headers: this.getApiHeaders(),
                body: JSON.stringify(annotationData)
            });

            if (response.ok) {
                const result = await response.json();
                this.annotations[result.annotation_id] = {
                    ...annotationData,
                    id: result.annotation_id
                };
                this.annotationsList = Object.keys(this.annotations);
                this.currentAnnotationIndex = this.annotationsList.length - 1;

                this.setSaveStatus('saved');
                this.showMessage('Annotation saved successfully', 'success');
                this.updateStats();
                this.updateNavigationControls();
                // Only clear form for manual saves, not auto-saves
                if (!this.isAutoSaving) {
                    this.clearForm();
                }
            } else {
                throw new Error('Failed to save annotation');
            }
        } catch (error) {
            console.error('Save error:', error);
            this.setSaveStatus('error');
            this.showMessage('Error saving annotation', 'error');
        } finally {
            this.isSaving = false;
        }
    }

    clearForm() {
        const form = document.getElementById('annotation-form');
        form.reset();

        this.clearImageSelections();
        this.selectedBeforeImage = null;
        this.selectedAfterImage = null;

        this.clearImageDisplay('before');
        this.clearImageDisplay('after');

        this.disableForm();
        this.updateSaveButtonState();

        this.showMessage('Form cleared', 'info');
    }

    navigateAnnotation(direction) {
        if (this.annotationsList.length === 0) return;

        this.currentAnnotationIndex += direction;

        if (this.currentAnnotationIndex < 0) {
            this.currentAnnotationIndex = this.annotationsList.length - 1;
        } else if (this.currentAnnotationIndex >= this.annotationsList.length) {
            this.currentAnnotationIndex = 0;
        }

        this.loadAnnotation(this.annotationsList[this.currentAnnotationIndex]);
        this.updateNavigationControls();
    }

    loadAnnotation(annotationId) {
        const annotation = this.annotations[annotationId];
        if (!annotation) {
            console.error('Annotation not found:', annotationId);
            return;
        }

        console.log('Loading annotation:', annotationId, annotation);
        console.log('Available images:', this.images.map(img => img.filename));
        console.log('Looking for:', annotation.before_image, annotation.after_image);

        // Find and select images
        const beforeImage = this.images.find(img => img.filename === annotation.before_image);
        const afterImage = this.images.find(img => img.filename === annotation.after_image);

        if (beforeImage && afterImage) {
            this.selectedBeforeImage = beforeImage;
            this.selectedAfterImage = afterImage;

            this.displayImage(beforeImage, 'before');
            this.displayImage(afterImage, 'after');

            // Update form
            document.getElementById('edit-description').value = annotation.edit_description;
            document.getElementById('edit-tags').value = annotation.metadata?.tags?.join(', ') || '';
            document.getElementById('difficulty').value = annotation.metadata?.difficulty || '';

            this.enableForm();
            this.updateImageSelections();
            this.updateSaveButtonState();
        } else {
            console.error('Images not found for annotation:', {
                beforeImage: annotation.before_image,
                afterImage: annotation.after_image,
                foundBefore: !!beforeImage,
                foundAfter: !!afterImage
            });

            // Still populate the form even if images aren't found
            document.getElementById('edit-description').value = annotation.edit_description;
            document.getElementById('edit-tags').value = annotation.metadata?.tags?.join(', ') || '';
            document.getElementById('difficulty').value = annotation.metadata?.difficulty || '';

            // Show placeholder for missing images
            this.clearImageDisplay('before');
            this.clearImageDisplay('after');

            // Show error message
            this.showMessage(`Images not found for annotation: ${annotation.before_image}, ${annotation.after_image}`, 'error');
        }
    }

    updateImageSelections() {
        this.clearImageSelections();

        document.querySelectorAll('.image-item').forEach(item => {
            const filename = item.dataset.filename;
            if (this.selectedBeforeImage && filename === this.selectedBeforeImage.filename) {
                item.classList.add('before-selected');
            }
            if (this.selectedAfterImage && filename === this.selectedAfterImage.filename) {
                item.classList.add('selected');
            }
        });
    }

    updateNavigationControls() {
        const prevBtn = document.getElementById('prev-annotation');
        const nextBtn = document.getElementById('next-annotation');
        const currentSpan = document.getElementById('current-annotation');

        const hasAnnotations = this.annotationsList.length > 0;

        console.log('Updating navigation controls:', {
            hasAnnotations,
            currentIndex: this.currentAnnotationIndex,
            totalAnnotations: this.annotationsList.length,
            annotationsList: this.annotationsList
        });

        prevBtn.disabled = !hasAnnotations;
        nextBtn.disabled = !hasAnnotations;

        if (hasAnnotations) {
            // Ensure current index is valid
            if (this.currentAnnotationIndex < 0 || this.currentAnnotationIndex >= this.annotationsList.length) {
                console.warn('Invalid annotation index, resetting to 0');
                this.currentAnnotationIndex = 0;
                // Load the first annotation
                if (this.annotationsList.length > 0) {
                    this.loadAnnotation(this.annotationsList[0]);
                }
            }
            currentSpan.textContent = `Annotation ${this.currentAnnotationIndex + 1} of ${this.annotationsList.length}`;
        } else {
            currentSpan.textContent = 'No annotations yet';
            this.currentAnnotationIndex = -1;
        }
    }

    // Method to manually refresh the current state - useful for debugging
    refreshCurrentAnnotation() {
        console.log('Refreshing current annotation...');
        if (this.currentAnnotationIndex >= 0 && this.annotationsList.length > 0) {
            const currentAnnotationId = this.annotationsList[this.currentAnnotationIndex];
            if (currentAnnotationId) {
                this.loadAnnotation(currentAnnotationId);
            }
        }
        this.updateNavigationControls();
    }

    async exportData(format) {
        try {
            this.showMessage(`Exporting data as ${format.toUpperCase()}...`, 'info');

            const response = await fetch(this.getApiUrl(`/api/export/${format}`));

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                const filename = this.datasetName ? `${this.datasetName}_annotations.${format}` : `annotations.${format}`;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);

                this.showMessage(`Data exported as ${format.toUpperCase()}`, 'success');
            } else {
                throw new Error('Export failed');
            }
        } catch (error) {
            console.error('Export error:', error);
            this.showMessage('Error exporting data', 'error');
        }
    }

    async exportFullDataset() {
        if (!this.datasetName) {
            this.showMessage('No dataset selected', 'error');
            return;
        }

        try {
            this.showMessage('Exporting full dataset...', 'info');

            const response = await fetch(`/api/datasets/${this.datasetName}/export`);

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `dataset_${this.datasetName}.zip`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);

                this.showMessage('Full dataset exported successfully', 'success');
            } else {
                throw new Error('Export failed');
            }
        } catch (error) {
            console.error('Export error:', error);
            this.showMessage('Error exporting dataset', 'error');
        }
    }

    async updateStats() {
        try {
            const response = await fetch(this.getApiUrl('/api/stats'));
            if (response.ok) {
                const stats = await response.json();
                document.getElementById('annotation-count').textContent =
                    `${stats.total_annotations} annotation${stats.total_annotations !== 1 ? 's' : ''}`;
                document.getElementById('image-count').textContent =
                    `${this.images.length} image${this.images.length !== 1 ? 's' : ''}`;
            }
        } catch (error) {
            console.error('Error updating stats:', error);
        }
    }

    handleKeyboardShortcuts(event) {
        // Ctrl+S or Cmd+S to save
        if ((event.ctrlKey || event.metaKey) && event.key === 's') {
            event.preventDefault();
            this.saveAnnotation();
        }

        // Arrow keys for navigation (only if no input is focused)
        if (!['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target.tagName)) {
            if (event.key === 'ArrowLeft') {
                this.navigateAnnotation(-1);
            } else if (event.key === 'ArrowRight') {
                this.navigateAnnotation(1);
            }
            // Delete key to delete current annotation
            if (event.key === 'Delete') {
                this.deleteCurrentAnnotation();
            }
        }

        // Escape to clear form
        if (event.key === 'Escape') {
            this.clearForm();
        }
    }

    autoSave() {
        console.log('Auto-save triggered');
        const description = document.getElementById('edit-description').value.trim();
        if (this.selectedBeforeImage && this.selectedAfterImage && description) {
            // Check if we're not already saving
            const saveBtn = document.getElementById('save-annotation');
            if (saveBtn && !saveBtn.disabled && !this.isSaving) {
                console.log('Auto-save conditions met, saving...');
                this.isAutoSaving = true;
                this.showMessage('Auto-saving...', 'info');
                this.saveAnnotation().finally(() => {
                    this.isAutoSaving = false;
                });
            } else {
                console.log('Auto-save skipped - save button disabled or already saving');
            }
        } else {
            console.log('Auto-save skipped - missing images or description');
        }
    }

    setSaveStatus(status) {
        const statusElement = document.getElementById('save-status');
        statusElement.className = `save-status ${status}`;

        switch (status) {
            case 'saving':
                statusElement.textContent = 'Saving...';
                break;
            case 'saved':
                statusElement.textContent = 'Saved';
                setTimeout(() => {
                    statusElement.className = 'save-status';
                    statusElement.textContent = 'Ready';
                }, 2000);
                break;
            case 'error':
                statusElement.textContent = 'Save Error';
                setTimeout(() => {
                    statusElement.className = 'save-status';
                    statusElement.textContent = 'Ready';
                }, 3000);
                break;
            default:
                statusElement.textContent = 'Ready';
        }
    }

    showMessage(message, type = 'info') {
        const messageArea = document.getElementById('message-area');
        messageArea.textContent = message;
        messageArea.className = `message-area ${type}`;

        // Clear message after timeout (longer for errors)
        const timeout = type === 'error' ? 8000 : type === 'warning' ? 6000 : 5000;
        setTimeout(() => {
            messageArea.textContent = '';
            messageArea.className = 'message-area';
        }, timeout);
    }

    showProgress(show) {
        const progressBar = document.getElementById('upload-progress');
        progressBar.style.display = show ? 'block' : 'none';

        if (show) {
            const progressFill = progressBar.querySelector('.progress-fill');
            progressFill.style.width = '0%';
        }
    }

    closeModal() {
        document.getElementById('annotation-modal').style.display = 'none';
    }

    toggleImageForDeletion(filename, isSelected) {
        if (isSelected) {
            this.markedForDeletion.add(filename);
        } else {
            this.markedForDeletion.delete(filename);
        }

        // Update visual state
        const imageItem = document.querySelector(`[data-filename="${filename}"]`);
        if (imageItem) {
            imageItem.classList.toggle('marked-for-deletion', isSelected);
        }

        this.updateClearButtonStates();
    }

    selectAllImages() {
        this.images.forEach(image => {
            this.markedForDeletion.add(image.filename);
        });
        this.renderImageGrid();
        this.showMessage(`Selected ${this.images.length} images for deletion`, 'info');
    }

    async clearSelectedImages() {
        const selectedFiles = Array.from(this.markedForDeletion);
        if (selectedFiles.length === 0) {
            this.showMessage('No images selected for deletion', 'warning');
            return;
        }

        const confirmed = confirm(`Are you sure you want to delete ${selectedFiles.length} selected image(s)? This will also remove any related annotations and cannot be undone.`);
        if (!confirmed) return;

        try {
            this.showMessage('Deleting selected images...', 'info');

            const requestBody = {
                filenames: selectedFiles,
                clear_all: false
            };
            if (this.datasetName) {
                requestBody.dataset = this.datasetName;
            }

            const response = await fetch('/api/images/clear', {
                method: 'POST',
                headers: this.getApiHeaders(),
                body: JSON.stringify(requestBody)
            });

            if (response.ok) {
                const result = await response.json();

                // Remove deleted images from local array
                this.images = this.images.filter(img => !selectedFiles.includes(img.filename));

                // Clear selection
                this.markedForDeletion.clear();

                // Clear any current selections if they were deleted
                if (this.selectedBeforeImage && selectedFiles.includes(this.selectedBeforeImage.filename)) {
                    this.selectedBeforeImage = null;
                    this.clearImageDisplay('before');
                }
                if (this.selectedAfterImage && selectedFiles.includes(this.selectedAfterImage.filename)) {
                    this.selectedAfterImage = null;
                    this.clearImageDisplay('after');
                }

                // Update UI
                this.renderImageGrid();
                this.updateStats();
                this.loadExistingData(); // Refresh annotations

                this.showMessage(
                    `Deleted ${result.removed_files} images and ${result.removed_annotations} annotations`,
                    'success'
                );
            } else {
                throw new Error('Failed to delete images');
            }
        } catch (error) {
            console.error('Error deleting images:', error);
            this.showMessage('Error deleting selected images', 'error');
        }
    }

    async clearAllImages() {
        if (this.images.length === 0) {
            this.showMessage('No images to clear', 'info');
            return;
        }

        const confirmed = confirm(`Are you sure you want to delete ALL ${this.images.length} images? This will also remove all annotations and cannot be undone.`);
        if (!confirmed) return;

        try {
            this.showMessage('Clearing all images...', 'info');

            const requestBody = {
                clear_all: true
            };
            if (this.datasetName) {
                requestBody.dataset = this.datasetName;
            }

            const response = await fetch('/api/images/clear', {
                method: 'POST',
                headers: this.getApiHeaders(),
                body: JSON.stringify(requestBody)
            });

            if (response.ok) {
                const result = await response.json();

                // Clear everything
                this.images = [];
                this.annotations = {};
                this.annotationsList = [];
                this.markedForDeletion.clear();
                this.selectedBeforeImage = null;
                this.selectedAfterImage = null;
                this.currentAnnotationIndex = -1;

                // Update UI
                this.renderImageGrid();
                this.clearImageDisplay('before');
                this.clearImageDisplay('after');
                this.clearForm();
                this.updateStats();
                this.updateNavigationControls();

                this.showMessage(
                    `Cleared ${result.removed_files} images and ${result.removed_annotations} annotations`,
                    'success'
                );
            } else {
                throw new Error('Failed to clear images');
            }
        } catch (error) {
            console.error('Error clearing images:', error);
            this.showMessage('Error clearing all images', 'error');
        }
    }

    updateClearButtonStates() {
        const clearSelectedBtn = document.getElementById('clear-selected-btn');
        const clearAllBtn = document.getElementById('clear-all-btn');
        const selectAllBtn = document.getElementById('select-all-btn');

        const hasSelection = this.markedForDeletion.size > 0;
        const hasImages = this.images.length > 0;
        const allSelected = hasImages && this.markedForDeletion.size === this.images.length;

        clearSelectedBtn.disabled = !hasSelection;
        clearAllBtn.disabled = !hasImages;

        // Update select all button text
        selectAllBtn.textContent = allSelected ? 'Deselect All' : 'Select All';
        selectAllBtn.onclick = () => {
            if (allSelected) {
                this.markedForDeletion.clear();
                this.renderImageGrid();
                this.showMessage('Deselected all images', 'info');
            } else {
                this.selectAllImages();
            }
        };
    }

    async deleteCurrentAnnotation() {
        if (this.currentAnnotationIndex < 0 || this.annotationsList.length === 0) {
            this.showMessage('No annotation selected to delete', 'warning');
            return;
        }

        const currentAnnotationId = this.annotationsList[this.currentAnnotationIndex];
        const annotation = this.annotations[currentAnnotationId];

        if (!annotation) {
            this.showMessage('Annotation not found', 'error');
            return;
        }

        const confirmed = confirm(`Are you sure you want to delete this annotation?\n\nEdit: ${annotation.edit_description?.substring(0, 100)}${annotation.edit_description?.length > 100 ? '...' : ''}`);
        if (!confirmed) return;

        try {
            this.showMessage('Deleting annotation...', 'info');

            const response = await fetch(`/api/annotations/${currentAnnotationId}`, {
                method: 'DELETE',
                headers: this.getApiHeaders()
            });

            if (response.ok) {
                // Remove from local data
                delete this.annotations[currentAnnotationId];
                this.annotationsList = Object.keys(this.annotations);

                // Update current index
                if (this.annotationsList.length === 0) {
                    this.currentAnnotationIndex = -1;
                    this.clearForm();
                } else {
                    // Stay at the same index if possible, otherwise go to previous
                    if (this.currentAnnotationIndex >= this.annotationsList.length) {
                        this.currentAnnotationIndex = this.annotationsList.length - 1;
                    }
                    // Load the annotation at the current index
                    if (this.currentAnnotationIndex >= 0) {
                        this.loadAnnotation(this.annotationsList[this.currentAnnotationIndex]);
                    }
                }

                this.updateNavigationControls();
                this.updateStats();
                this.loadExistingData(); // Refresh to update image usage indicators
                this.showMessage('Annotation deleted successfully', 'success');
            } else {
                throw new Error('Failed to delete annotation');
            }
        } catch (error) {
            console.error('Delete error:', error);
            this.showMessage('Error deleting annotation', 'error');
        }
    }

    async changeFilter(filterType) {
        this.currentFilter = filterType;
        console.log('Changing filter to:', filterType);

        try {
            this.showMessage('Applying filter...', 'info');

            const response = await fetch(this.getApiUrl(`/api/images/filtered?filter=${filterType}`));
            if (response.ok) {
                const data = await response.json();
                this.images = data.images || [];
                this.filterCounts = data.counts || {};

                this.updateFilterCount();
                this.renderImageGrid();
                this.showMessage(`Filter applied: ${filterType}`, 'success');
            } else {
                throw new Error('Failed to apply filter');
            }
        } catch (error) {
            console.error('Filter error:', error);
            this.showMessage('Error applying filter', 'error');
        }
    }

    updateFilterCount() {
        const filterCountElement = document.getElementById('filter-count');
        if (!filterCountElement || !this.filterCounts) return;

        const counts = this.filterCounts;
        const filterSelect = document.getElementById('image-filter');
        const currentFilter = filterSelect.value;

        let countText = '';
        switch (currentFilter) {
            case 'all':
                countText = `${counts.total || 0} total`;
                break;
            case 'unused':
                countText = `${counts.unused || 0} unused`;
                break;
            case 'before-only':
                countText = `${counts.before_only || 0} before only`;
                break;
            case 'after-only':
                countText = `${counts.after_only || 0} after only`;
                break;
            case 'used':
                countText = `${counts.used || 0} used`;
                break;
        }

        filterCountElement.textContent = `(${countText})`;
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.annotator = new ImageEditAnnotator();
});