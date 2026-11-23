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
| `helpdesk_ticket` | Požadavek: povinný `title`, `description` a `author`; volitelný `assignee`, `category` a `updated_by`; dále `status`, `priority`, časová razítka, `resolved_at` a SLA termíny první reakce a vyřešení. |
| `helpdesk_comment` | Komentář k požadavku s autorem, textem a časem vytvoření. `is_internal` rozlišuje interní poznámku od zprávy viditelné uživateli. |
| `helpdesk_ticketsolution` | Jedno aktuální řešení požadavku: text, technik a čas vytvoření. `ticket_id` je unikátní, takže požadavek má nula nebo jedno řešení. |
| `helpdesk_tickethistory` | Audit změn požadavku. Ukládá změněné pole, textové původní a nové hodnoty, autora změny a čas. Nově sledovaná pole jsou název, popis, stav, priorita, technik, kategorie a čas vyřešení; starší záznamy mohou navíc obsahovat `updated_by`. |
| `helpdesk_ticketattachment` | Příloha požadavku uložená mimo databázi, její původní název, nahrávající a čas. Stažení vždy ověřuje přístup k požadavku. |
| `helpdesk_notification` | Aplikační upozornění pro příjemce, navázané na požadavek; `read_at` je prázdné, dokud není upozornění přečteno. |
| `helpdesk_ticketfeedback` | Jedno hodnocení (1–5) za požadavek, volitelný komentář a čas odeslání. |
| `helpdesk_knowledgearticle` | Článek znalostní báze se slugem, kategorií, autorem a příznakem publikace. |

## Kardinality

- Uživatel vytvoří `0..N` požadavků; každý požadavek má právě jednoho autora.
- Aktivní technik nebo administrátor helpdesku může mít přiřazeno `0..N` požadavků; požadavek může být nepřiřazený nebo mít jednoho takového řešitele.
- Kategorie může obsahovat `0..N` požadavků; každý požadavek může mít nejvýše jednu kategorii.
- Požadavek má `0..N` komentářů a `0..N` záznamů historie.
- Požadavek má `0..1` řešení. Vztah 1:1 je záměrný: model uchovává jedno aktuální řešení, nikoliv všechny historické pokusy. Opětovné otevření požadavku existující řešení nesmaže; při dalším vyřešení se upraví tento záznam.
- Požadavek může mít více příloh, upozornění a komentářů, nejvýše jedno hodnocení a více záznamů historie.
- Kategorie může obsahovat více článků znalostní báze; článek může být bez kategorie.

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

SLA termíny se počítají z priority a času vytvoření v kalendářních hodinách:
kritická priorita má 1 hodinu na první reakci a 8 hodin na vyřešení, vysoká
4/24 hodin, normální 8/72 hodin a nízká 24/120 hodin. Změna priority termíny
přepočítá. Čekající stav SLA zatím nepozastavuje.

## Integrita a mazání

**Databáze** vynucuje jedinečnost primárních klíčů a názvů kategorií,
referenční integritu cizích klíčů a povolené hodnoty pro role, stavy, priority
a názvy sledovaných polí historie. Kontroluje také, že `resolved_at` není
starší než `created_at`.

**Aplikační logika** dále kontroluje povolené přechody stavů a to, že
přiřazený uživatel je aktivní technik nebo administrátor helpdesku. Tyto
kontroly probíhají v modelu a jsou dostupné formulářům i API. Uživateli nelze
odebrat roli technika nebo administrátora, dokud má přiřazené požadavky;
nejdřív je nutné je přeřadit. Přímý zápis SQL nebo
`QuerySet.update()` obchází validaci modelu; databázové omezení proto zůstává
důležité pro pravidla, která lze vyjádřit jako `CHECK` nebo cizí klíč.

Interní poznámky zobrazují pouze technici a administrátoři; veřejné komentáře
se zobrazují také autorovi požadavku. Přílohy se obsluhují přes přístupem
chráněný pohled, nikoli přes veřejné URL. Uživatel může ohodnotit pouze svůj
vyřešený nebo uzavřený požadavek. Nepublikované články vidí pouze technici a
administrátoři.

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

Přílohy mají limit 5 MB a povolené přípony PDF, JPG, PNG a TXT. E-mailová
upozornění používají nastavitelný Django e-mail backend; lokální výchozí
backend zapisuje zprávy do konzole.
