# IT Helpdesk

Webová aplikace pro evidenci, správu a řešení IT problémů a požadavků.

## Funkce
- registrace a přihlášení uživatele
- vytváření a správa požadavků
- role uživatel / technik / administrátor
- přehled dashboardu a statistik
- komentáře k požadavkům
- základní REST API včetně endpointů pro tickets

## Spuštění projektu

### 1) Vytvoření virtuálního prostředí
Windows:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2) Instalace závislostí

```powershell
pip install -r requirements.txt
```

### 3) Migrace databáze

```powershell
python manage.py migrate
```

### 4) Vytvoření admin účtu

```powershell
python manage.py createsuperuser
```

### 5) Spuštění aplikace

```powershell
python manage.py runserver
```

Aplikace běží na adrese: http://127.0.0.1:8000/

## Přístup pro demo
Výchozí admin účet byl vytvořen:
- username: admin
- password: admin123

## API
- GET /api/tickets/
- POST /api/tickets/
- GET /api/tickets/<id>/
- PUT/PATCH /api/tickets/<id>/
- DELETE /api/tickets/<id>/
