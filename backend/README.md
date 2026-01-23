# BoraMatch AI – Backend

This is the **backend service** for **BoraMatch AI**, an intelligent resume screening system that matches candidate CVs to job descriptions using a hybrid AI approach combining semantic similarity with keyword relevance.

Built to serve as a **plug-and-play API** for recruiters, BoraMatch helps streamline the hiring process by quickly identifying the most relevant candidates for a given role.

## Tech Stack

- **Python 3.10+**
- **FastAPI** – For building high-performance REST APIs
- **spaCy** – NLP preprocessing
- **KeyBERT** – For keyword extraction from text
- **Sentence Transformers** – Embedding-based semantic similarity
- **Google Drive API** – Resume storage and access
- **Uvicorn** – ASGI server for local/dev use

