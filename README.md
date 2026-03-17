# Finance AI Backend (Django)

Backend service for Finance AI, built with Django and Django REST Framework.

## 1) Requirements

- Python 3.12+ (recommended)
- MySQL server
- Git

## 2) Clone and setup

```bash
git clone https://github.com/DATN-2026/Finance_AI_BE.git
cd Finance_AI_BE
```

If the project is already at repository root after clone, run:

```bash
cd finance_ai
```

## 3) Create virtual environment

### Windows (PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### macOS/Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

## 4) Install libraries

```bash
pip install --upgrade pip
pip install Django djangorestframework drf-spectacular PyJWT bcrypt mysqlclient
```

Notes:

- If `mysqlclient` fails to build on Windows, install Visual C++ Build Tools.
- You can temporarily switch to `PyMySQL` if needed.

## 5) Environment variables

Create `.env` from sample:

```bash
cp .env.example .env
```

On Windows CMD:

```cmd
copy .env.example .env
```

Then edit `.env` with your real values:

- `SECRET_KEY`
- DB settings (`DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`)
- JWT settings
- SMTP email settings

## 6) Run migrations

```bash
python manage.py migrate
```

## 7) Run server

```bash
python manage.py runserver
```

API docs:

- Swagger: `http://127.0.0.1:8000/api/docs/`
- ReDoc: `http://127.0.0.1:8000/api/redoc/`

## 8) Security notes

- Do not commit `.env`.
- Do not commit local IDE secrets.
- Keep `.env.example` only with placeholder values.
