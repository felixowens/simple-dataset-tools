# Image Edit Dataset Annotator – Phased POC Plan

A lightweight, single‑developer tool that lets you import a folder of images, rapidly pair them (A → B), write an edit prompt, track progress, and export the result in a machine‑readable format.  Everything runs **locally** with no external services.

---

## 1 · Baseline Assumptions

| # | Assumption                                                  | Notes                                                 |
| - | ----------------------------------------------------------- | ----------------------------------------------------- |
| 1 | Personal, single‑user workflow                              | No authentication, no concurrent users.               |
| 2 | Images live on disk inside each *project* directory         | We store relative file paths only.                    |
| 3 | Export → **JSONL** (default) and **CSV**                    | One row per completed task.                           |
| 4 | Similarity = perceptual hash (**pHash**) + Hamming distance | Good‑enough recall for suggesting candidate B images. |
| 5 | State management = **React Context + URL params**           | No external store like Zustand/Redux.                 |
| 6 | No Docker                                                   | `python -m venv` and `npm install` are enough.        |

---

## 2 · Tech Stack (optimised for speed & simplicity)

| Layer         | Choice                                         | Rationale                                                               |
| ------------- | ---------------------------------------------- | ----------------------------------------------------------------------- |
| UI            | **React + Vite + TypeScript + Tailwind**       | Instant dev server, utility CSS, strong TS DX.                          |
| State         | React Context + `useReducer` + URLSearchParams | URL encodes the wizard step & IDs, context holds transient bits.        |
| Backend       | **FastAPI (Python 3.12)**                      | Minimal boilerplate, async, first‑class type hints, Uvicorn dev server. |
| DB            | **SQLite via SQLModel**                        | File‑backed, shipped in stdlib; zero infra.                             |
| Image hashing | **imagehash + Pillow**                         | One‑liner `imagehash.phash(Image.open(path))`.                          |
| Messaging     | **Server‑Sent Events (SSE)**                   | Push hash progress to UI without websocket boilerplate.                 |
| Packaging     | Pure `venv` + `npm` scripts                    | Keep onboarding friction near zero.                                     |

---

## 3 · Phase Roadmap

> **Estimates** assume 1 engineer; each phase ≈ 0.5–1 day.

| Phase  | Goal                | Key Steps                                                                                                                                                       |
| ------ | ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **P1** | *Project skeleton*  | ① `pnpm create vite` → starter React app with Typescript. ② FastAPI stub with `/ping`. ③ CORS + Axios handshake.                                                                |
| **P2** | *Data model*        | ① Define SQLModel entities `Project`, `Image`, `Task`. ② CRUD endpoints. ③ React form to create / open project.                                                 |
| **P3** | *Ingest & Hash*     | ① Drag‑and‑drop `<input type="file" multiple>` → POST `/upload`. ② Backend saves into `projects/<id>/images/`. ③ Async pHash compute; SSE progress bar.         |
| **P4** | *Task generator*    | ① For each image, fetch N most‑similar (self‑join on Hamming ≤ h). ② Insert `Task` rows with candidate B list.                                                  |
| **P5** | *Annotation UI*     | ① Wizard page shows A image + candidate B thumbnails. ② Keyboard shortcuts `1‑9` to pick, `s` skip, `d` delete. ③ Prompt textarea autofocused; PUT `/task/:id`. |
| **P6** | *Progress & Resume* | ① Dashboard counts (total / done / skipped). ② Resume button jumps to first unfinished. ③ Option to re‑queue skipped.                                           |
| **P7** | *Export*            | ① `/export/jsonl` streams file. ② `/export/csv` alternative schema. ③ Download triggers in browser.                                                             |
| **P8** | *Polish*            | ① Dark‑mode toggle. ② Lightbox zoom on images. ③ Drag‑reorder candidate list.                                                                                   |

---

## 4 · User Flow (Mermaid)

```mermaid
flowchart TD
    subgraph Setup
        P[Create Project\nname + version]
        U[Upload Images]
        H[Compute pHash\nstore in DB]
    end

    subgraph Tasking
        T1[Generate Tasks\nsimilarity match]
        loopAnnotate{{Unfinished Task?}}
        A[Annotate Pair\nchoose B + prompt]
        S[Skip / Remove]
    end

    subgraph Completion
        D[Dashboard\nprogress stats]
        E[Export\nJSONL / CSV]
    end

    P --> U --> H --> T1 --> loopAnnotate
    loopAnnotate -- yes --> A --> loopAnnotate
    loopAnnotate -- skip --> S --> loopAnnotate
    loopAnnotate -- no --> D --> E
```

---

## 5 · Export Schema Examples

### 5.1  JSONL (default)

```json
{"a": "images/0001.jpg", "b": "images/0001_edit.jpg", "prompt": "turn sky pink"}
```

### 5.2  CSV

```csv
a,b,prompt
images/0001.jpg,images/0001_edit.jpg,"turn sky pink"
```
