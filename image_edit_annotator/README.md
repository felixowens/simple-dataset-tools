# Image Edit Prompt Annotator

A web-based tool for creating and managing image edit prompt datasets. This application allows you to upload images, pair them as "before" and "after" examples, and annotate the transformations with detailed descriptions.

## What It Does

The Image Edit Annotator helps you build datasets for training image editing AI models by:

- **Creating image pairs**: Select "before" and "after" images to demonstrate transformations
- **Adding detailed annotations**: Describe what changes were made between the images
- **Managing multiple datasets**: Organize your work into separate projects
- **Tracking image usage**: See which images have been used and which are still available
- **Exporting data**: Download your annotations in various formats for training

## Getting Started

### Prerequisites

- Python 3.7 or higher
- Web browser (Chrome, Firefox, Safari, Edge)

### Installation

1. Navigate to the image_edit_annotator directory:
   ```bash
   cd image_edit_annotator
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python app.py
   ```

4. Open your web browser and go to: `http://localhost:5000`

## How to Use

### 1. Dataset Management

When you first access the tool, you'll be prompted to select or create a dataset:

- **Create New Dataset**: Click "Create Dataset" and provide a name and description
- **Select Existing Dataset**: Choose from your previously created datasets
- **Import Dataset**: Upload a ZIP file containing a previously exported dataset

### 2. Uploading Images

Once in a dataset, you can add images:

- **Drag & Drop**: Drag image files directly onto the upload area
- **Browse Files**: Click "Choose Images" to select files from your computer
- **Supported Formats**: JPG, PNG, GIF, BMP, WebP (max 16MB per file)

### 3. Creating Annotations

To create an annotation:

1. **Select Before Image**: Click on an image in the gallery - it will be highlighted in blue
2. **Select After Image**: Click on another image - it will be highlighted in gray
3. **Add Description**: In the right panel, describe the transformation in detail
4. **Add Tags** (optional): Add comma-separated tags like "color-correction, brightness"
5. **Set Difficulty** (optional): Choose Easy, Medium, or Hard
6. **Save**: Click "Save Annotation" or press Ctrl+S

### 4. Image Filtering

Use the filter dropdown to efficiently manage your images:

- **All Images**: Show all uploaded images
- **Unused Images**: Show only images not used in any annotations (great for finding new material)
- **Before Images Only**: Show images used only as "before" examples
- **After Images Only**: Show images used only as "after" examples  
- **Used Images**: Show all images that have been used in annotations

Each filter shows a count of matching images, helping you track your progress.

### 5. Visual Indicators

Images in the gallery show usage indicators:
- **B** (blue badge): Used as a "before" image
- **A** (orange badge): Used as an "after" image
- **B+A** (green badge): Used in both positions
- No badge: Unused image

### 6. Managing Annotations

Navigate through your annotations using:

- **Previous/Next Buttons**: Browse through all annotations
- **Arrow Keys**: Use left/right arrows for quick navigation
- **Delete Current**: Remove the currently displayed annotation
- **Delete Key**: Quick deletion with keyboard shortcut

### 7. Bulk Operations

Manage multiple images at once:

- **Select All/Deselect All**: Toggle selection of all visible images
- **Clear Selected**: Delete chosen images and their related annotations
- **Clear All**: Remove all images and annotations (with confirmation)

### 8. Exporting Data

Export your work in multiple formats:

- **JSON**: Structured data for programmatic use
- **CSV**: Spreadsheet-compatible format
- **JSONL**: One annotation per line, ideal for machine learning
- **Full Dataset ZIP**: Complete package with images and annotations

## Keyboard Shortcuts

- **Ctrl+S** (or Cmd+S): Save current annotation
- **Left/Right Arrows**: Navigate between annotations
- **Delete**: Delete current annotation
- **Escape**: Clear the form

## Tips for Effective Use

### Creating Quality Datasets

1. **Be Descriptive**: Write detailed descriptions of what changed between images
2. **Use Consistent Language**: Develop a vocabulary for common transformations
3. **Tag Systematically**: Use consistent tags to categorize edit types
4. **Mix Difficulty Levels**: Include easy, medium, and hard examples

### Workflow Recommendations

1. **Upload in Batches**: Add 20-50 images at a time for manageable sessions
2. **Use the "Unused" Filter**: Regularly check for images you haven't annotated yet
3. **Start with Easy Examples**: Begin with obvious transformations before tackling subtle ones
4. **Export Regularly**: Back up your work by exporting datasets periodically

### Image Preparation

- **Consistent Sizing**: While not required, similar image sizes work better
- **Clear Differences**: Ensure the before/after changes are visible
- **Good Quality**: Use clear, well-lit images when possible
- **Unique Filenames**: Avoid duplicate filenames to prevent confusion

## Troubleshooting

### Images Not Loading
- Check that images are in supported formats (JPG, PNG, GIF, BMP, WebP)
- Ensure files are under 16MB
- Refresh the page if images seem stuck

### Annotations Not Saving
- Verify both before and after images are selected
- Ensure the description field is not empty
- Check your internet connection

### Performance Issues
- Large datasets (>1000 images) may load slowly
- Consider splitting very large datasets into smaller projects
- Close other browser tabs to free up memory

## Data Format

### Annotation Structure
Each annotation contains:
- **Before Image**: Filename of the original image
- **After Image**: Filename of the transformed image  
- **Edit Description**: Detailed text description of changes
- **Tags**: Comma-separated keywords
- **Difficulty**: Easy, Medium, or Hard
- **Metadata**: Creation time, update time, etc.

### Export Formats

**JSON**: Hierarchical structure with full metadata
**CSV**: Flat format suitable for spreadsheets
**JSONL**: One JSON object per line for streaming/ML use

## Security & Privacy

- All data is stored locally on your machine
- No images or annotations are sent to external servers
- Datasets are isolated - each project's data is separate
- Regular backups via export are recommended

## Technical Details

### File Structure

```
image_edit_annotator/
├── app.py                 # Flask web server
├── data_manager.py        # Annotation data management
├── dataset_manager.py     # Dataset organization
├── templates/
│   ├── index.html         # Main annotation interface
│   └── dataset_selection.html # Dataset management
├── static/
│   ├── style.css          # UI styling
│   ├── script.js          # Frontend functionality
│   └── uploads/           # Legacy image storage
├── datasets/              # Dataset-specific storage
│   └── [dataset_name]/
│       ├── images/        # Dataset images
│       ├── annotations.json # Dataset annotations
│       └── metadata.json  # Dataset information
├── exports/               # Generated export files
└── requirements.txt       # Python dependencies
```

### API Endpoints

- `GET /`: Main annotation interface
- `GET /datasets`: Dataset selection page
- `POST /api/upload`: Upload image files
- `GET /api/images`: List all images
- `GET /api/images/filtered`: Get filtered images by usage
- `GET /api/annotations`: Get all annotations
- `POST /api/annotations`: Save new annotation
- `PUT /api/annotations/<id>`: Update annotation
- `DELETE /api/annotations/<id>`: Delete annotation
- `GET /api/export/<format>`: Export annotations
- `GET /api/stats`: Get annotation statistics
- `GET /api/datasets`: List all datasets
- `POST /api/datasets`: Create new dataset
- `GET /api/datasets/<name>/export`: Export full dataset

## Support

For issues, questions, or feature requests, please check the project documentation or create an issue in the project repository.