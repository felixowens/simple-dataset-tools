# Image Edit Dataset Annotator

A lightweight tool for creating image edit datasets by pairing images and writing edit prompts.

## Phase 1 - Project Skeleton ✅

This phase implements the basic full-stack structure with CORS communication between React frontend and FastAPI backend.

## Project Structure

```
image-edit-annotator/
├── frontend/          # React + Vite + TypeScript + Tailwind
│   ├── src/
│   │   ├── App.tsx    # Main component with API status check
│   │   ├── api.ts     # Axios configuration
│   │   └── ...
│   └── package.json
├── backend/           # FastAPI Python
│   ├── main.py        # FastAPI app with /ping endpoint
│   └── requirements.txt
└── README.md
```

## Setup Instructions

### Backend Setup

1. Create Python virtual environment:

```bash
cd backend
python -m venv venv
source venv/bin/activate 
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the FastAPI server:

```bash
python main.py
```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. Install dependencies:

```bash
cd frontend
pnpm install
```

2. Start the development server:

```bash
pnpm run dev
```
