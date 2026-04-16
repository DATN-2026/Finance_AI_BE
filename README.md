# Finance AI Backend (Django)

Backend service for Finance AI, built with Django and Django REST Framework.

## 1) Requirements

- Python 3.12+
- MySQL server
- Git

## 2) Clone and setup

```bash
git clone https://github.com/DATN-2026/Finance_AI_BE.git
cd Finance_AI_BE
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
pip install -r requirements.txt
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

Then update `.env` with real values. Required keys used by source code:

```env
SECRET_KEY=your_django_secret
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

DB_ENGINE=django.db.backends.mysql
DB_NAME=finance_ai
DB_USER=root
DB_PASSWORD=your_db_password
DB_HOST=127.0.0.1
DB_PORT=3307

JWT_SECRET_KEY=your_jwt_secret
JWT_ALGORITHM=HS512
JWT_ISSUER=finance_ai.com
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=30
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=youremail@example.com
EMAIL_HOST_PASSWORD=your-email-password-or-app-password
```

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
