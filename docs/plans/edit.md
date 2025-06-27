# Image Edit Annotator Reimplementation Plan

## Analysis of Current Issues

The existing tool has several architectural and UX problems:

- Complex Flask architecture with multiple managers and convoluted routing
- Poor separation of concerns between frontend/backend
- Inefficient image handling with complex upload/serve logic
- Buggy state management in the JavaScript
- Outdated dependencies (Flask 2.3.3, old Pillow)
- Complex dataset management that adds unnecessary complexity
- Poor error handling and user feedback

## Technology Stack Choice

### Backend: FastAPI (instead of Flask)

- Modern, fast, automatic API documentation
- Better async support for file operations
- Built-in validation with Pydantic
- Cleaner dependency injection

### Frontend: Modern Vanilla JS with Web Components

- No framework overhead, lighter and faster
- Custom elements for reusable components
- Modern ES6+ features
- Better state management patterns

### Storage: SQLite + File System

- Simple, reliable, no external dependencies
- Better data integrity than JSON files
- Faster queries for filtering/statistics

## Architecture Design

### 1. Backend Structure

```
annotator/
├── main.py              # FastAPI app entry point
├── models.py            # Pydantic models & SQLite schemas
├── database.py          # Database connection & operations
├── api/
│   ├── images.py        # Image upload/serve endpoints
│   ├── annotations.py   # Annotation CRUD operations
│   └── exports.py       # Export functionality
├── static/              # Frontend assets
└── uploads/             # Image storage
```

### 2. Frontend Architecture

- Single Page Application with component-based architecture
- State Management: Central store with event-driven updates
- Image Grid Component: Virtualized for performance with large datasets
- Annotation Form Component: Real-time validation and auto-save
- Keyboard Navigation: Comprehensive shortcuts for power users

### 3. Data Model Simplification

```sql
-- Single table for annotations
CREATE TABLE annotations (
    id INTEGER PRIMARY KEY,
    before_image TEXT NOT NULL,
    after_image TEXT NOT NULL,
    description TEXT NOT NULL,
    tags TEXT,
    difficulty TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Index for fast filtering
CREATE INDEX idx_images ON annotations(before_image, after_image);
```

## Implementation Plan

### Phase 1: Core Backend (Day 1)

1. Setup FastAPI project with modern dependencies
2. Implement SQLite database with proper schema
3. Create image upload/serve endpoints with proper validation
4. Build annotation CRUD API with filtering support
5. Add export functionality (JSON, CSV, JSONL)

### Phase 2: Modern Frontend (Day 2)

1. Create responsive HTML structure with CSS Grid/Flexbox
2. Build image grid component with lazy loading
3. Implement annotation form with real-time validation
4. Add keyboard shortcuts and navigation
5. Create drag-and-drop upload with progress indicators

### Phase 3: UX Enhancements (Day 3)

1. Add image filtering (used/unused/by-type)
2. Implement bulk operations (select multiple, delete)
3. Add annotation navigation (prev/next with keyboard)
4. Create export UI with format selection
5. Add confirmation dialogs for destructive actions

### Phase 4: Polish & Testing (Day 4)

1. Error handling and user feedback
2. Performance optimization for large datasets
3. Responsive design for different screen sizes
4. Data persistence and backup features
5. Documentation and setup instructions

## Key UX Improvements

### 1. Streamlined Workflow

- Single-screen interface - no dataset selection complexity
- Direct image pairing - click two images to create pair
- Inline editing - edit annotations without form resets
- Visual feedback - clear indication of image usage status

### 2. Enhanced Image Management

- Thumbnail generation for faster loading
- Image metadata display (dimensions, file size)
- Smart filtering with search functionality
- Batch operations with multi-select

### 3. Better Annotation Experience

- Auto-save as you type
- Annotation templates for common edit types
- Quick tags with autocomplete
- Annotation history with undo/redo

### 4. Improved Performance

- Lazy loading for large image sets
- Virtual scrolling for smooth navigation
- Background processing for exports
- Client-side caching for better responsiveness

## Technical Benefits

- 50% fewer lines of code with cleaner architecture
- Faster startup and response times
- Better error handling with proper HTTP status codes
- Modern web standards with progressive enhancement
- Easier maintenance with clear separation of concerns
- Better testability with isolated components

This reimplementation will provide a much cleaner, faster, and more maintainable tool while significantly improving the user experience for creating image edit datasets.
