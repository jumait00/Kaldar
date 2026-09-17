# Expense Tracker — Web Version

A multi-user web application based on the original terminal Expense Tracker project.

## Stack

- Python 3.13+
- Django 6.1.1
- SQLite for development
- PostgreSQL recommended for production
- WhiteNoise for static files
- Gunicorn for production WSGI serving

## Features

- User signup/login/logout
- Per-user private account data
- Initial cash and digital balances
- Expense transactions
- Deposit
- Withdraw digital money into cash
- Repay loan
- Give loan
- Receive loan
- Take loan
- Balance dashboard
- Transaction history
- Search/filter transactions
- CSRF protection
- Password validation
- Database transactions with row locking
- Production security settings
- Immutable financial transaction history

## Local setup — Windows PowerShell

```powershell
py -3.14 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py check
python manage.py runserver
```

Open:

http://127.0.0.1:8000/

## Important accounting design

The original CSV stored balances as snapshots on every row. The web version keeps this useful audit information but uses a real database and an `Account` row for the current balances.

Transactions are intentionally immutable. Deleting an old transaction would make later balance snapshots inconsistent. A correction should therefore be recorded as a new transaction.

## Production deployment

The project supports a `DATABASE_URL` environment variable. Use PostgreSQL for a public multi-user deployment. The current PostgreSQL driver is Psycopg 3.

Do NOT deploy with `DEBUG=True`.

Set:

```text
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<long-random-secret>
DJANGO_ALLOWED_HOSTS=your-domain.com
CSRF_TRUSTED_ORIGINS=https://your-domain.com
```

Set a PostgreSQL `DATABASE_URL`, for example:

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
```

Collect static files:

```bash
python manage.py collectstatic --noinput
```

Run Gunicorn:

```bash
gunicorn expense_tracker.wsgi:application
```

For HTTPS, use a hosting provider/reverse proxy that terminates TLS.

## Existing CSV data

The original CSV can be imported into this database, but because the old CSV represents a single user's account, it should be imported only into that user's account. Do not expose the CSV publicly.

## Before public launch

- Use PostgreSQL
- Set a strong secret key
- Set DEBUG=False
- Configure ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS
- Enable HTTPS
- Configure backups
- Add email-based password reset
- Add rate limiting / login protection
- Review privacy policy and terms
- Test restore procedures


## PythonAnywhere deployment

This project is prepared for PythonAnywhere's manual Django/WSGI deployment.

1. Upload or clone this project into a directory such as `~/kaldar`.
2. In a PythonAnywhere Bash console, create a virtualenv using the same Python version selected for the web app. Python 3.13 is a supported choice for this project.
3. Activate the virtualenv and run:
   ```bash
   cd ~/kaldar
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py check --deploy
   python manage.py test
   ```
4. In the PythonAnywhere Web tab, create a **Manual configuration** web app using the same Python version as the virtualenv.
5. Set the web app's virtualenv to your virtualenv path, for example:
   `/home/YOURUSERNAME/.virtualenvs/kaldar`
6. Edit the PythonAnywhere WSGI configuration file and use:
   ```python
   import os
   import sys

   path = "/home/YOURUSERNAME/kaldar"
   if path not in sys.path:
       sys.path.insert(0, path)

   os.environ.setdefault("DJANGO_SETTINGS_MODULE", "expense_tracker.settings")

   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```
7. Set these production values in a `.env` file in the project directory (or through the environment-variable mechanism available to your PythonAnywhere account):
   ```text
   DJANGO_SECRET_KEY=<long-random-secret>
   DJANGO_DEBUG=False
   DJANGO_ALLOWED_HOSTS=YOURUSERNAME.pythonanywhere.com
   PYTHONANYWHERE_DOMAIN=YOURUSERNAME.pythonanywhere.com
   ```
8. If you use the default SQLite database, make sure the project directory is persistent and writable. For a larger production deployment, use a supported external database and set `DATABASE_URL`.
9. In the PythonAnywhere Web tab, add a static-files mapping:
   - URL: `/static/`
   - Directory: `/home/YOURUSERNAME/kaldar/staticfiles`
10. Reload the web app.

Do not run `manage.py runserver` as the production server on PythonAnywhere. The Web tab's WSGI configuration runs the application.

### Important PythonAnywhere note

PythonAnywhere's web server and static-file mapping are configured outside the project files. Therefore no ZIP archive can make the Web-tab configuration automatic. The project itself contains the correct Django WSGI application, static settings, production settings, migrations, and automated tests, but the Web tab still requires the one-time configuration above.
