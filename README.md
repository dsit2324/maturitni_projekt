# IT Helpdesk

Webová aplikace pro evidenci a řešení IT požadavků. Projekt je maturitní práce oboru Informační technologie a používá Django, Django REST Framework a SQLite.

## Funkce

- Registrace a přihlášení; nově registrované účty mají roli uživatele.
- Uživatel vidí své požadavky a může přidávat komentáře. Technik vidí všechny požadavky a může měnit jejich stav, prioritu a přiřazení.
- Administrátor může požadavky spravovat a mazat. Role se přidělují v administraci Django; veřejná registrace roli technika ani administrátora nenabízí.
- Historie změn a komentáře jsou dostupné v detailu požadavku. Záznam řešení lze spravovat v administraci Django.
- Přehled požadavků a REST API.

## Spuštění pomocí Dockeru

Je potřeba Docker s Docker Compose.

```bash
docker compose up --build
```

Při startu se automaticky provedou databázové migrace. Aplikace poběží na <http://localhost:8000/>. Databáze SQLite je uložena v pojmenovaném svazku `helpdesk_data`, takže data zůstanou zachována i po zastavení kontejneru.

Migrace také převedou dosavadní účty bez příznaku administrátora na roli uživatele, aby zneužitelná role z dřívější veřejné registrace nezůstala aktivní. Ověřené techniky je potřeba následně znovu nastavit v administraci Django.

Vytvoření administrátorského účtu:

```bash
docker compose exec web python manage.py createsuperuser
```

Zastavení aplikace:

```bash
docker compose down
```

Odstranění databáze a všech uložených dat:

```bash
docker compose down --volumes
```

Docker konfigurace je určena pro lokální vývoj. Django development server nepoužívejte pro veřejné produkční nasazení.

## Spuštění bez Dockeru

Je potřeba Python 3.12 nebo novější.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Na Windows aktivujte prostředí příkazem `.venv\Scripts\activate`. Aplikace bude dostupná na <http://127.0.0.1:8000/>.

Při spuštění v jiném prostředí nezapomeňte provést `python manage.py migrate`, aby se vytvořilo aktuální databázové schéma.

## REST API

| Metoda | Cesta | Popis |
| --- | --- | --- |
| `GET`, `POST` | `/api/tickets/` | Seznam a vytvoření požadavků |
| `GET`, `PUT`, `PATCH`, `DELETE` | `/api/tickets/<id>/` | Zobrazení a úprava požadavku |

Administrace Django je dostupná na `/admin/`.

Úpravy přes API odpovídají rolím: běžný uživatel může vytvářet požadavky, ale nemůže měnit jejich stav ani je mazat; mazání je vyhrazené administrátorovi.

## Databázový diagram

Databázové schéma ve formátu DBML pro [dbdiagram.io](https://dbdiagram.io/) je v [docs/database.dbml](docs/database.dbml). Diagram zachycuje aplikační tabulky; interní tabulky Django autentizace, relace, migrací a administrace jsou vynechány.
<img width="1459" height="683" alt="diagram" src="https://github.com/user-attachments/assets/fd215bb3-db64-4b8d-af75-f85c071c0952" />

## Testy

```bash
python manage.py test
```
