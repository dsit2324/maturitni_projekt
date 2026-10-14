# Databázový model

Tento dokument popisuje aplikační tabulky z diagramu [database.dbml](./database.dbml),
jejich kardinality a pravidla, která nejsou zřejmá pouze z cizích klíčů.
Tabulky autentizace, oprávnění, relací a administrace vytváří Django a nejsou
součástí aplikačního diagramu.

## Datový slovník

| Tabulka | Význam a důležité atributy |
| --- | --- |
| `helpdesk_user` | Účet zděděný z Django `AbstractUser`. `role` určuje aplikační roli (`user`, `technician`, `admin`); `is_staff` a `is_superuser` jsou samostatná oprávnění Django. Pro datum registrace se používá zděděné `date_joined`. |
| `helpdesk_category` | Číselník kategorií: jedinečný `name`, volitelný popis a `created_at`. Požadavek může být dočasně bez kategorie. |
| `helpdesk_ticket` | Požadavek: povinný `title`, `description` a `author`; volitelný `assignee`, `category` a `updated_by`; dále `status`, `priority`, časová razítka a `resolved_at`. |
| `helpdesk_comment` | Veřejný komentář k požadavku s autorem, textem a časem vytvoření. Interní komentáře zatím model nepodporuje. |
| `helpdesk_ticketsolution` | Jedno aktuální řešení požadavku: text, technik a čas vytvoření. `ticket_id` je unikátní, takže požadavek má nula nebo jedno řešení. |
| `helpdesk_tickethistory` | Audit změn požadavku. Ukládá změněné pole, textové původní a nové hodnoty, autora změny a čas. Nově sledovaná pole jsou název, popis, stav, priorita, technik, kategorie a čas vyřešení; starší záznamy mohou navíc obsahovat `updated_by`. |

## Kardinality

- Uživatel vytvoří `0..N` požadavků; každý požadavek má právě jednoho autora.
- Technik může mít přiřazeno `0..N` požadavků; požadavek může být nepřiřazený nebo mít jednoho technika.
- Kategorie může obsahovat `0..N` požadavků; každý požadavek může mít nejvýše jednu kategorii.
- Požadavek má `0..N` komentářů a `0..N` záznamů historie.
- Požadavek má `0..1` řešení. Vztah 1:1 je záměrný: model uchovává jedno aktuální řešení, nikoliv všechny historické pokusy. Opětovné otevření požadavku existující řešení nesmaže; při dalším vyřešení se upraví tento záznam.

## Pravidla životního cyklu

Povolené změny stavů jsou:

| Aktuální stav | Povolený další stav |
| --- | --- |
| `new` | `accepted` |
| `accepted` | `in_progress`, `pending` |
| `in_progress` | `pending`, `resolved` |
| `pending` | `in_progress` |
| `resolved` | `closed`, `in_progress` (opětovné otevření) |
| `closed` | `in_progress` (opětovné otevření) |

Nastavení stejného stavu je povolené při úpravě jiných údajů. Nový požadavek
začíná vždy ve stavu `new`. Čas `resolved_at` se nastaví při přechodu do
`resolved`, zůstává zachován při uzavření a smaže se při opětovném otevření.
Po opětovném vyřešení se nastaví nový čas.

## Integrita a mazání

**Databáze** vynucuje jedinečnost primárních klíčů a názvů kategorií,
referenční integritu cizích klíčů a povolené hodnoty pro role, stavy, priority
a názvy sledovaných polí historie. Kontroluje také, že `resolved_at` není
starší než `created_at`.

**Aplikační logika** dále kontroluje povolené přechody stavů a to, že přiřazený
uživatel má roli technika. Tyto kontroly probíhají v modelu a jsou dostupné
formulářům i API. Roli technika nelze změnit, dokud má uživatel přiřazené
požadavky; nejdřív je nutné je přeřadit. Přímý zápis SQL nebo
`QuerySet.update()` obchází validaci modelu; databázové omezení proto zůstává
důležité pro pravidla, která lze vyjádřit jako `CHECK` nebo cizí klíč.

Uživatelské účty se mají deaktivovat pomocí `is_active=False`, ne fyzicky
mazat. Smazání přes Django ORM nebo administraci je blokováno, pokud je účet veden jako autor požadavku,
komentáře, řešení nebo auditní změny. Při smazání požadavku se jeho komentáře,
řešení a historie odstraní spolu s ním. Smazání kategorie nastaví u navázaných
požadavků `category_id` na `NULL`; smazání přiřazeného technika nebo posledního
editora zruší příslušnou vazbu bez odstranění požadavku.

## Indexy a rozšíření

Složené indexy pokrývají seznam požadavků autora, filtrování požadavků podle
technika a stavu a časové osy komentářů a historie. Pro tyto vazby nahrazují
samostatné indexy cizích klíčů, aby se zbytečně neduplikovaly.

Model zatím nezahrnuje přílohy ani interní komentáře. Případná podpora
interních poznámek by vyžadovala nejen příznak u komentáře, ale také kontrolu
oprávnění při čtení dat v každém rozhraní včetně API.
