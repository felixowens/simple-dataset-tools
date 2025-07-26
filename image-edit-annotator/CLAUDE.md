# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Image Dataset Annotator - a versatile tool supporting both image editing datasets and traditional image captioning datasets for machine learning training.

**Purpose:** 
- **Edit Mode**: Import image folders, automatically suggest similar pairs using perceptual hashing, annotate with edit descriptions for A→B image transformations
- **Caption Mode**: Import individual images and add descriptive captions for traditional image-text datasets

Export capabilities include JSONL format and AI-toolkit structure for various ML training workflows.

**Tech Stack:**
- Frontend: React + Vite + TypeScript + Tailwind CSS
- Backend: Go + SQLite
- Image similarity: goimagehash (pHash + Hamming distance)

## Development Commands

### Frontend (`frontend/`)
```bash
cd frontend
pnpm install          # Install dependencies
pnpm dev              # Start development server (http://localhost:5173)
pnpm build            # Build for production
pnpm lint             # Run ESLint
```

### Backend (`backend/`)
```bash
cd backend
go mod tidy           # Install dependencies
go run .              # Start development server (http://localhost:8080)
go build              # Build binary
```

## Architecture

### Data Flow

#### Edit Projects (Image A → Image B with edit descriptions)
1. **Project Creation**: User creates "edit" project with name/version
2. **Image Upload**: Images uploaded to `backend/data/projects/{id}/images/`
3. **Hash Generation**: Perceptual hashes computed for similarity matching
4. **Task Generation**: Similar image pairs automatically suggested using pHash similarity
5. **Annotation**: User selects image B from candidates and writes edit prompt describing the transformation
6. **Export**: JSONL format `{"a": "path/img1.jpg", "b": "path/img2.jpg", "prompt": "edit description"}` or AI-toolkit structure

#### Caption Projects (Single images with descriptive captions)
1. **Project Creation**: User creates "caption" project with name/version
2. **Image Upload**: Images uploaded to `backend/data/projects/{id}/images/`
3. **Task Generation**: One caption task created per image (no similarity matching needed)
4. **Annotation**: User writes descriptive caption for each image
5. **Export**: JSONL format `{"image": "path/img.jpg", "caption": "descriptive text"}`

### Key Files
- `backend/models.go`: Project, Image, Task, CaptionTask entities and database schema
- `backend/database.go`: SQLite operations and migrations for both project types
- `backend/main.go`: HTTP handlers and API endpoints for both edit and caption workflows
- `frontend/src/components/AnnotationWizard.tsx`: Edit project annotation interface (A→B image pairs)
- `frontend/src/components/CaptionAnnotationWizard.tsx`: Caption project interface (single image captioning)
- `frontend/src/components/FileUpload.tsx`: Image upload component
- `frontend/src/api.ts`: Frontend API client with support for both project types

### State Management
- React Context + useReducer for application state
- URL params encode wizard step and active IDs (`/wizard?step=annotate&taskId=123`)
- Backend maintains persistent state in SQLite database

### API Endpoints

#### Core Project Management
- `GET /ping` - Health check
- `POST /projects` - Create new project (specify projectType: "edit" or "caption")
- `GET /projects` - List all projects
- `POST /projects/{id}/upload` - Upload images

#### Edit Project Endpoints (A→B image pairs)
- `GET /projects/{id}/tasks` - Get edit annotation tasks
- `PUT /tasks/{id}` - Update edit task annotation
- `POST /projects/{id}/generate-tasks` - Generate edit tasks using similarity matching

#### Caption Project Endpoints (Single image captions)
- `GET /projects/{id}/caption-tasks` - Get caption tasks
- `PUT /caption-tasks/{id}` - Update caption task

#### Export
- `GET /projects/{id}/export/jsonl` - Export JSONL (format varies by project type)
- `GET /projects/{id}/export/ai-toolkit` - Export AI-toolkit format (edit projects only)

## Development Notes

- **Dual-mode support** - Application now supports both edit and caption project types
- **Single-user workflow** - No authentication required
- **Local-first** - No external services, everything runs locally
- **Experimental stage** - Breaking changes and database resets are acceptable
- **URL-first design** - Application state encoded in URLs where possible
- **Backward compatibility** - Existing projects default to "edit" type via database migration
- Always run build commands on both frontend/backend to ensure no errors
- Database file: `backend/data/app.db` (SQLite)
- Images stored: `backend/data/projects/{project-id}/images/`

### Project Type Differences
- **Edit projects**: Complex workflow with image pairs, similarity matching, A→B annotations, AI-toolkit export
- **Caption projects**: Simple workflow with single images, direct captioning, 1:1 image→caption, JSONL export only