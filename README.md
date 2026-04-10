# BoraMatch AI Agent

BoraMatch AI Agent is an AI-powered recruitment screening system designed to help hiring teams review resumes faster and shortlist stronger candidates with more consistency.

It combines resume parsing, job requirement extraction, and hybrid matching logic to rank applicants against a job description and present recruiter-friendly results through a simple dashboard.

## Why BoraMatch

Recruiters often spend too much time manually reviewing CVs, especially when applications arrive in large numbers. BoraMatch helps reduce that effort by:

* extracting resume content automatically
* comparing applicants against job requirements
* assigning match scores and confidence labels
* surfacing relevant keywords and strengths
* giving recruiters a faster shortlist workflow

## Current MVP Scope

BoraMatch currently supports:

* job creation
* resume upload
* resume text extraction
* AI-assisted job requirement parsing
* hybrid candidate matching
* recruiter-facing match views
* ATS-style data structure with separate candidates and applications concepts

## Product Flow

### Candidate Side

1. A job is created in the system.
2. A candidate uploads a resume.
3. The backend extracts and processes the resume.
4. The application is matched against the target job.

### Recruiter Side

1. Recruiter views available jobs.
2. Recruiter opens a specific job.
3. Recruiter sees matched applicants.
4. Recruiter reviews match score, confidence, and relevant details.

## Architecture Overview

### Backend

* FastAPI
* Modular API structure
* Resume parsing utilities
* Matching engine
* Job parsing logic
* Local database files for MVP persistence

### Frontend

* Next.js
* Recruiter dashboard pages
* API routes for frontend-backend communication
* Modal-based UI interactions

## Project Structure

```text
boramatch-ai-agent/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── data/
│   │   ├── utils/
│   │   └── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── pages/api/
│   ├── src/app/
│   ├── src/components/
│   └── package.json
└── README.md
```

## Core Matching Logic

BoraMatch uses a hybrid approach to make ranking more useful than pure keyword search.

The matching flow combines:

* semantic similarity
* keyword relevance
* extracted job requirements
* recruiter-readable confidence output

Example result:

```json
{
  "score": 0.82,
  "confidence": "Strong Match",
  "matched_keywords": ["Python", "Machine Learning", "FastAPI"]
}
```

## Main Backend Modules

* `upload_resume.py` — handles candidate resume upload flow
* `match_resumes.py` — runs matching logic
* `job_postings.py` — handles job creation
* `list_jobs.py` — returns available jobs
* `resume_by_job.py` — fetches resumes/applications for a job
* `resume_parser.py` — extracts text from resumes
* `job_parser_llm.py` — parses job descriptions into structured requirements
* `matching.py` — computes candidate-job match results

## Frontend Views

* recruiter dashboard
* recruiter job matches page
* recruiter applicants page

## Local Development

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Environment Notes

Do not commit sensitive files:

The repository is already configured to ignore development-only and sensitive files.

## Roadmap

Planned improvements for productization include:

* better recruiter dashboard polish
* stronger candidate profile presentation
* persistent ATS-style storage layer
* improved evaluation and scoring transparency
* exportable recruiter reports
*emailing and scheduling interview 
* production deployment setup
* multi-job and multi-company support

## Positioning

BoraMatch is being developed as a practical AI layer for recruitment workflows, with a focus on helping teams screen applicants more efficiently without replacing recruiter judgment.

## Demo and Outreach

A demo video has already been prepared and shared publicly as part of product validation and outreach.
https://www.loom.com/share/8a585a26020c49d1846a2e8b30230617

👩‍Author
Vivian Njuguna
AI Developer | Full Stack Engineer
Founder — Vivi Solutions

Support
If you like this project, give it a ⭐ on GitHub!
