# ATS Resume Generator

React + Django REST Framework application for generating ATS-friendly resumes from an original resume, target job description, custom prompt, and uploaded resume file.

## Features

- Administrator-created users, login, logout, and authenticated API access.
- CRUD APIs for original resumes and job descriptions.
- Uploaded resume files are used automatically as each resume's generation template.
- Resume generation from resume text, job description, and custom prompt.
- Optional OpenAI integration through `OPENAI_API_KEY`.
- Local deterministic generator fallback when no AI key is configured.
- DOCX placeholder replacement for:
  - `{{FULL_NAME}}`
  - `{{CONTACT_INFO}}`
  - `{{PROFESSIONAL_SUMMARY}}`
  - `{{TECHNICAL_SKILLS}}`
  - `{{PROFESSIONAL_EXPERIENCE}}`
  - `{{PROJECTS}}`
  - `{{EDUCATION}}`
  - `{{CERTIFICATIONS}}`
- ATS keyword score with matched and missing keywords.
- Generation history and authenticated DOCX downloads.

## Project Structure

```text
backend/
  accounts/
  resumes/
  jobs/
  templates_app/
  generator/
  config/
frontend/
  src/
    api/
    components/
    context/
    pages/
```

## Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

The app creates a default administrator after migrations:

```text
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_EMAIL=admin@blue.com
DEFAULT_ADMIN_PASSWORD=qwe123QWE!@#
```

New users are created by an administrator from the in-app Users page.

By default the project expects PostgreSQL:

```text
POSTGRES_DB=ats_resume_generator
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

For quick local testing without PostgreSQL, set:

```text
USE_SQLITE=1
```

## Frontend Setup

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Open `http://localhost:5173`.

## Chrome Extension Side Panel

This repo includes a local Chrome extension in `extension/` for capturing job descriptions from the browser.

1. Start the backend and frontend.
2. Open Chrome and go to `chrome://extensions`.
3. Enable Developer mode.
4. Choose "Load unpacked" and select the `extension/` folder.
5. Open a job posting, select the full job description, and press `Ctrl+Space`.

The extension opens the side panel, loads the app at `http://localhost:5173/job`, and fills the Job Description form with the selected text and source URL. Continue by saving the job, then choose the resume and prompt, and generate as usual.

If Chrome has already assigned `Ctrl+Space` to another shortcut, open `chrome://extensions/shortcuts` and set "Capture selected job description" manually.

## Optional AI Setup

Create a fresh OpenAI API key and set these in `backend/.env`:

```text
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4.1-mini
```

Do not commit `backend/.env` or paste real API keys into chat, docs, or source files.
If no key is provided, the backend still generates a resume using the local fallback service.

## API Summary

| Feature | Method | Endpoint |
| --- | --- | --- |
| Login | POST | `/api/auth/login/` |
| Logout | POST | `/api/auth/logout/` |
| Current user | GET | `/api/auth/me/` |
| Users | CRUD | `/api/auth/users/` |
| Resumes | CRUD | `/api/resumes/` |
| Jobs | CRUD | `/api/jobs/` |
| Generate | POST | `/api/generate-resume/` |
| History | GET | `/api/generations/` |
| Detail | GET | `/api/generations/{id}/` |
| Download | GET | `/api/generations/{id}/download/` |

## Template Notes

Upload a `.docx` resume when creating a resume to use that document's layout as the generation template. If no upload-backed template exists, the app creates a clean DOCX output automatically.

## MVP Limitations

- Paste-based original resume input only.
- DOCX uploads provide the best layout preservation.
- Placeholder replacement is intentionally simple and ATS-friendly.
- Advanced background jobs, payments, team accounts, and PDF parsing are out of scope.
