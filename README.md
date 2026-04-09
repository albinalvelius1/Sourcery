# Sourcery

Sourcery is a local tool that automatically finds academic papers for your text and inserts `\cite{}` tags into it. It also generates a `.bib` file for the sources it finds.

It uses a local LLM to do its best to extract keywords and verify sources, but uses standard Python string matching to insert the citations so your original text never gets rewritten or messed up by it.

## Requirements

You'll need a few things installed to run this:

1. **Python 3.11+**
2. **Node.js**
3. **Ollama** (Running locally on port 11434)

Make sure you have the `qwen3.5:9b` model pulled in Ollama before running:
```bash
ollama pull qwen3.5:9b
```

## Setup

First, install the backend dependencies:
```bash
cd backend
python -m pip install -r requirements.txt
```

Then, install the frontend dependencies:
```bash
cd frontend
npm install
```

## How to Run

You need to run both the frontend and backend at the same time in separate terminal windows.

**Terminal 1 (Backend):**
```bash
cd backend
python main.py
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```

Then just open `http://localhost:5173` in your browser. 
There's a slider on the page you can use to control how strict or lenient the LLM is when matching papers to your text.

---
*Note: This application was vibe coded using Google Antigravity.*
