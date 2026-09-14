# IT Helpdesk

Webová aplikace určená pro evidenci, správu a řešení IT problémů a požadavků. Projekt je vytvořen jako závěrečná maturitní práce pro obor Informační technologie.

## 1. Popis projektu

IT Helpdesk umožňuje uživatelům jednoduše nahlásit technický problém a pracovníkům IT podpory umožňuje tyto problémy evidovat, přiřazovat, řešit a následně uzavírat.

Cílem projektu je vytvořit přehledný systém, který může být použit například ve škole, firmě nebo jiné organizaci, kde je potřeba evidovat větší množství IT požadavků.

Aplikace bude obsahovat uživatelské účty, databázi požadavků, systém rolí, správu požadavků a přehledové statistiky.

---

# 2. Hlavní funkce

### Uživatel

Uživatel bude moci:

* vytvořit účet,
* přihlásit se,
* vytvořit nový požadavek,
* zobrazit své požadavky,
* sledovat stav požadavku,
* zobrazit historii řešení,
* přidávat komentáře,
* případně uzavřít nebo doplnit svůj požadavek.

### Technik

Technik bude moci:

* zobrazit všechny přidělené požadavky,
* převzít požadavek,
* změnit jeho stav,
* změnit prioritu,
* přidat komentář,
* zapsat způsob řešení,
* označit požadavek jako vyřešený,
* zobrazit historii požadavku.

### Administrátor

Administrátor bude mít rozšířená oprávnění:

* správa uživatelů,
* správa techniků,
* správa požadavků,
* změna rolí,
* úprava kategorií problémů,
* přehled statistik,
* správa celé aplikace.

---

# 3. Stav požadavku

Každý požadavek bude mít jeden ze stavů:

* **Nový** – požadavek byl právě vytvořen.
* **Přijatý** – požadavek byl zaregistrován technickou podporou.
* **Řeší se** – technik na problému pracuje.
* **Čeká se** – řešení je dočasně pozastaveno.
* **Vyřešený** – problém byl vyřešen.
* **Uzavřený** – požadavek byl definitivně uzavřen.

---

# 4. Priorita

Každý požadavek bude mít nastavenou prioritu:

* Nízká
* Normální
* Vysoká
* Kritická

Priorita pomůže technikům určit, kterým problémům je potřeba věnovat pozornost nejdříve.

---

# 5. Kategorie problémů

Požadavky budou možné zařadit například do kategorií:

* Hardware
* Software
* Síť
* Přihlášení
* Tiskárny
* Internet
* Účty
* Bezpečnost
* Ostatní

Kategorie bude možné v budoucnu rozšířit podle potřeby.

---

# 6. Technologie

Projekt bude vytvořen pomocí těchto technologií:

### Backend

* Python
* Django
* Django REST Framework

### Databáze

* SQLite pro vývoj
* PostgreSQL pro případné produkční nasazení

### Frontend

* HTML
* CSS
* Bootstrap
* JavaScript

### Další technologie

* Git
* GitHub
* REST API
* JSON

---

# 7. Struktura projektu

Příklad struktury projektu:

```text
it-helpdesk/
│
├── manage.py
│
├── requirements.txt
├── README.md
├── .gitignore
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── helpdesk/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── forms.py
│   ├── admin.py
│   └── serializers.py
│
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── tickets.html
│   └── ticket_detail.html
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
└── media/
```

Struktura se může během vývoje změnit podle konkrétní implementace.

---

# 8. Databázový model

Aplikace bude pracovat s několika hlavními entitami.

## User

Uživatel systému.

Obsahuje například:

* ID
* uživatelské jméno
* e-mail
* heslo
* roli
* datum registrace

## Ticket

Technický požadavek.

Obsahuje:

* ID
* název
* popis
* autora
* přiřazeného technika
* kategorii
* prioritu
* stav
* datum vytvoření
* datum poslední změny
* datum vyřešení

## Category

Kategorie požadavku.

Obsahuje:

* ID
* název
* popis

## Comment

Komentář k požadavku.

Obsahuje:

* ID
* požadavek
* autora
* text
* datum vytvoření

## Solution

Informace o způsobu vyřešení problému.

Obsahuje:

* ID
* požadavek
* technika
* popis řešení
* datum vyřešení

---

# 9. Uživatelské role

Aplikace bude využívat systém oprávnění.

```text
                    IT HELPDESK
                         │
          ┌──────────────┴──────────────┐
          │                             │
       Uživatel                       Technik
          │                             │
    vlastní požadavky            řešení požadavků
          │                             │
          └──────────────┬──────────────┘
                         │
                   Administrátor
                         │
                kompletní správa
```

Uživatel nebude mít přístup k administrátorským funkcím.

---

# 10. Dashboard

Po přihlášení bude uživatel přesměrován na hlavní stránku aplikace.

Dashboard může zobrazovat například:

* počet všech požadavků,
* počet nových požadavků,
* počet požadavků v řešení,
* počet vyřešených požadavků,
* počet kritických požadavků,
* poslední vytvořené požadavky.

Administrátor navíc uvidí statistiky celé aplikace.

---

# 11. Statistiky

Aplikace bude obsahovat statistickou část.

Možné statistiky:

* počet požadavků podle stavu,
* počet požadavků podle priority,
* počet požadavků podle kategorie,
* počet požadavků podle technika,
* počet vyřešených požadavků,
* počet požadavků za jednotlivé měsíce.

Statistiky mohou být zobrazeny pomocí grafů.

---

# 12. Vyhledávání a filtrování

Uživatelé s odpovídajícími oprávněními budou moci požadavky vyhledávat a filtrovat.

Filtrování bude možné například podle:

* stavu,
* priority,
* kategorie,
* technika,
* autora,
* data vytvoření.

---

# 13. REST API

Součástí projektu bude také REST API umožňující komunikaci s aplikací prostřednictvím HTTP požadavků.

Příklad endpointů:

```text
GET    /api/tickets/
GET    /api/tickets/1/
POST   /api/tickets/
PUT    /api/tickets/1/
PATCH  /api/tickets/1/
DELETE /api/tickets/1/
```

API bude vracet data ve formátu JSON.

Příklad:

```json
{
    "id": 1,
    "title": "Nefunguje internet",
    "status": "Řeší se",
    "priority": "Vysoká",
    "category": "Síť"
}
```

---

# 14. Bezpečnost

Aplikace bude obsahovat základní bezpečnostní prvky:

* přihlašování uživatelů,
* hashování hesel prostřednictvím Django,
* systém oprávnění,
* ochranu formulářů proti CSRF,
* kontrolu přístupu k jednotlivým funkcím,
* validaci vstupních údajů,
* oddělení uživatelských rolí.

---

# 15. Instalace

## Požadavky

Pro spuštění projektu je potřeba:

* Python 3.x
* pip
* Git

## Klonování projektu

```bash
git clone https://github.com/USERNAME/it-helpdesk.git
cd it-helpdesk
```

## Vytvoření virtuálního prostředí

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

## Instalace závislostí

```bash
pip install -r requirements.txt
```

## Migrace databáze

```bash
python manage.py migrate
```

## Vytvoření administrátora

```bash
python manage.py createsuperuser
```

## Spuštění aplikace

```bash
python manage.py runserver
```

Aplikace bude následně dostupná na:

```text
http://127.0.0.1:8000/
```

---

# 16. Testování

Projekt bude během vývoje testován.

Testovat se budou například:

* registrace uživatele,
* přihlášení,
* odhlášení,
* vytvoření požadavku,
* úprava požadavku,
* změna stavu,
* přiřazení technika,
* přidávání komentářů,
* oprávnění jednotlivých rolí,
* API endpointy,
* filtrování a vyhledávání.

---

# 17. Cíl projektu

Hlavním cílem projektu je vytvořit funkční webovou aplikaci, která bude řešit evidenci a správu IT požadavků.

Projekt má zároveň demonstrovat znalosti získané během studia oboru Informační technologie, především:

* programování,
* objektově orientovaného programování,
* databází,
* webových technologií,
* HTTP a REST API,
* práce s operačním systémem,
* verzovacích systémů,
* základů kybernetické bezpečnosti.

---

# 18. Možná rozšíření

Pokud bude dostatek času, je možné projekt rozšířit o:

* e-mailová upozornění,
* přílohy k požadavkům,
* automatické přidělování techniků,
* interní chat,
* historii změn,
* SLA a měření doby řešení,
* tmavý režim,
* responzivní design,
* export statistik do PDF/CSV,
* Docker,
* nasazení na server,
* pokročilejší REST API.

Rozšíření budou implementována pouze v případě, že budou dokončeny všechny základní funkce.

---

# 19. Harmonogram

### Září

* analýza požadavků
* návrh aplikace
* návrh databáze
* vytvoření Django projektu
* vytvoření základních modelů

### Říjen

* registrace a přihlášení
* uživatelské role
* vytváření požadavků
* seznam požadavků
* detail požadavku
* změna stavů
* přiřazování techniků

### Listopad

* komentáře
* filtrování
* vyhledávání
* dashboard
* statistiky
* REST API
* testování

### Prosinec

* opravy chyb
* optimalizace
* dokončení vzhledu
* dokumentace
* uživatelská příručka
* příprava prezentace a obhajoby

---

# 20. Výsledek

Výsledkem projektu bude kompletní webová aplikace umožňující organizaci evidovat, spravovat a řešit IT problémy.

Projekt bude navržen tak, aby byl použitelný jako základní helpdesk například pro školu nebo menší firmu.

---

## Dominik Svoboda

**Maturitní projekt – IT4 - obor Informační technologie**

Školní rok: **2026/2027**

Projekt: **IT Helpdesk**
