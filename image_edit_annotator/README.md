# Image Edit Prompt Dataset Annotation Tool

A web-based annotation tool for creating image edit prompt datasets. This tool allows you to import images, select pairs, and annotate the transformations between them.

## Features

- **Web-based Interface**: Clean, responsive UI accessible from any browser
- **Image Pair Selection**: Easy selection of before/after image pairs
- **Rich Annotations**: Add edit descriptions, tags, and difficulty levels
- **Multiple Export Formats**: Export data as JSON, CSV, or JSONL
- **Auto-save**: Automatic saving every 30 seconds
- **Keyboard Shortcuts**: Efficient navigation and saving
- **Progress Tracking**: Visual feedback and statistics

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**:
   ```bash
   python app.py
   ```

3. **Open in Browser**:
   Navigate to `http://localhost:5000`

## Usage Workflow

1. **Upload Images**: Click "Choose Images" to upload your image files
2. **Select Image Pairs**: 
   - Click an image to select it as the "before" image (orange border)
   - Click another image to select it as the "after" image (red border)
3. **Add Annotation**:
   - Enter a description of the edit/transformation
   - Add optional tags and difficulty level
   - Click "Save Annotation"
4. **Export Data**: Use export buttons to download your dataset

## Keyboard Shortcuts

- `Ctrl+S` / `Cmd+S`: Save current annotation
- `←` / `→`: Navigate between existing annotations
- `Escape`: Clear form and selections

## Export Formats

- **JSON**: Compatible with existing dataset format
- **CSV**: Tabular format for analysis
- **JSONL**: One JSON object per line (ML training format)

## File Structure

```
image_edit_annotator/
├── app.py                 # Flask web server
├── data_manager.py        # Data handling and export
├── templates/
│   └── index.html         # Main UI template
├── static/
│   ├── style.css          # Styling
│   ├── script.js          # Frontend logic
│   └── uploads/           # Uploaded images
├── exports/               # Generated export files
└── annotations.json       # Saved annotations
```

## API Endpoints

- `GET /`: Main annotation interface
- `POST /api/upload`: Upload image files
- `GET /api/images`: List uploaded images
- `GET /api/annotations`: Get all annotations
- `POST /api/annotations`: Save new annotation
- `PUT /api/annotations/<id>`: Update annotation
- `DELETE /api/annotations/<id>`: Delete annotation
- `GET /api/export/<format>`: Export data
- `GET /api/stats`: Get annotation statistics