# 🧠 RAG Agentic Knowledge Assistant (Demo)

This is a Retrieval-Augmented Generation (RAG) + AgentKit demo for regulated industries.  
It combines **FastAPI**, **Chroma**, **OCR**, and **OpenAI models** to power a secure knowledge assistant with agentic reasoning capabilities.

The stack is designed to run locally with Docker and includes:
- ✅ **FastAPI Backend** with ingestion, retrieval, OCR, and RAG
- ✅ **Next.js Frontend** with simple chat + file upload UI
- ✅ **OCR support** (Tesseract + Poppler) for scanned PDFs
- ✅ Integration of **CSV + PDF** data sources into Chroma vector DB
- ✅ **AgentKit** integration for multi-step reasoning (Agentic behavior)
- ✅ **Dockerized**, easy to run anywhere

## 🚀 Testing the setup

```

1. Run docker compose up -d
2. Visit http://localhost:3000
3. Upload a sample .pdf, .docx, .txt or .csv
4. Ask a question in the chat box
5. Verify answer and citations appear

```

## 🧱 Project Structure

```
rag_agentic_assistant/
├── backend/
│   ├── app.py
│   ├── core/
│   ├── rag/
│   ├── routers/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── pages/
│   ├── components/
│   ├── package.json
│   └── Dockerfile
├── data/
│   ├── pdfs/
│   └── csv/
│   └── docx/
│   └── txt/
├── index_store/
├── docker-compose.yml
├── .env
└── README.md
```

## 🚀 Features

- **RAG Backend**
  - FastAPI endpoints for PDF/CSV ingestion, search, chat
  - Uses `text-embedding-3-small` for embeddings and `gpt-4o-mini` for answers
  - Chroma as vector store
  - Auto-OCR for scanned PDFs

- **Frontend**
  - Next.j UI with chat box + file upload
  - Bearer token auth
  - Shows citations and metadata

- **Agentic Mode**
  - Leverages [OpenAI AgentKit](https://openai.com/index/introducing-agentkit/) to enable multi-step reasoning.

## ⚡️ Prerequisites

- Docker & Docker Compose (v2)
- OpenAI API Key with access to `gpt-4o-mini` and embeddings
- Tesseract and Poppler are installed inside the container

## 🧰 Environment Variables

Create a `.env` file in the project root:

```env
# Backend
OPENAI_API_KEY=sk-your-key
ANSWER_MODEL=gpt-4o-mini
EMBED_MODEL=text-embedding-3-small
BEARER_TOKEN=your-demo-token

DATA_DIR=/app/data
INDEX_DIR=/app/index_store/chroma_db

# Frontend
NEXT_PUBLIC_API_BASE=http://localhost:8000/api
NEXT_PUBLIC_BEARER_TOKEN=your-demo-token
```

## 🐳 Run with Docker

From the project root:

```bash
docker compose build
docker compose up
```

- Backend → http://localhost:8000
- Frontend → http://localhost:3000

## 📥 Ingesting Data

Upload via UI 

## 💬 Asking Questions

```bash
curl -X POST "http://localhost:8000/api/chat"   -H "Authorization: Bearer your-demo-token"   -H "Content-Type: application/json"   -d '{"query":"What are the encryption requirements?"}'
```

## 🧹 Resetting the Index

```bash
docker compose down -v
docker compose up --build
```

## 📝 Example Queries

- “What new regulatory measures have been introduced in the EU for digital banking in 2025?”  
- “When do the KYC policy changes become effective?”

## 📄 License

Demo project for client delivery. Not for redistribution.