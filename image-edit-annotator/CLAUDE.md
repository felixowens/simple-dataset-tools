# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Image Edit Dataset Annotator - a lightweight tool for pairing images (A → B), writing edit prompts, and exporting machine-readable datasets for training.

**Purpose:** Import image folders, automatically suggest similar pairs using perceptual hashing, annotate with edit descriptions, and export in JSONL/CSV formats or AI-toolkit structure.

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
1. **Project Creation**: User creates project with name/version
2. **Image Upload**: Images uploaded to `backend/data/projects/{id}/images/`
3. **Hash Generation**: Perceptual hashes computed for similarity matching
4. **Task Generation**: Similar image pairs automatically suggested
5. **Annotation**: User selects image B and writes edit prompt
6. **Export**: JSONL, CSV, or AI-toolkit folder structure

### Key Files
- `backend/models.go`: Project, Image, Task entities and database schema
- `backend/database.go`: SQLite operations and migrations
- `backend/main.go`: HTTP handlers and API endpoints
- `frontend/src/components/AnnotationWizard.tsx`: Main annotation interface
- `frontend/src/components/FileUpload.tsx`: Image upload component
- `frontend/src/api.ts`: Frontend API client

### State Management
- React Context + useReducer for application state
- URL params encode wizard step and active IDs (`/wizard?step=annotate&taskId=123`)
- Backend maintains persistent state in SQLite database

### API Endpoints
- `GET /ping` - Health check
- `POST /projects` - Create new project
- `GET /projects` - List all projects
- `POST /projects/{id}/upload` - Upload images
- `GET /projects/{id}/tasks` - Get annotation tasks
- `PUT /tasks/{id}` - Update task annotation
- `GET /projects/{id}/export/jsonl` - Export JSONL
- `GET /projects/{id}/export/ai-toolkit` - Export AI-toolkit format

## Development Notes

- **Single-user workflow** - No authentication required
- **Local-first** - No external services, everything runs locally
- **Experimental stage** - Breaking changes and database resets are acceptable
- **URL-first design** - Application state encoded in URLs where possible
- Always run build commands on both frontend/backend to ensure no errors
- Database file: `backend/data/app.db` (SQLite)
- Images stored: `backend/data/projects/{project-id}/images/`