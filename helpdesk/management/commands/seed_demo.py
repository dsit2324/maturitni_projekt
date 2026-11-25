from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from helpdesk.models import (
    Category,
    Comment,
    KnowledgeArticle,
    Notification,
    Ticket,
    TicketFeedback,
    TicketSolution,
    User,
)


class Command(BaseCommand):
    help = "Naplní databázi realistickými ukázkovými uživateli, tickety a články."

    def handle(self, *args, **options):
        now = timezone.now()

        def category(name):
            item, _ = Category.objects.get_or_create(name=name)
            return item

        hardware = category("Hardware")
        software = category("Software")
        network = category("Síť")
        accounts = category("Účty")
        printers = category("Tiskárny")
        security = category("Bezpečnost")

        users_data = [
            ("jana.novakova", "Jana", "Nováková", "jana@example.cz", "user"),
            ("petr.dvorak", "Petr", "Dvořák", "petr@example.cz", "user"),
            ("lucie.svoboda", "Lucie", "Svobodová", "lucie@example.cz", "user"),
        ]
        users = []
        for username, first_name, last_name, email, role in users_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "role": role,
                },
            )
            if created:
                user.set_password("demo1234")
                user.save()
            users.append(user)

        hardware_tech, _ = User.objects.get_or_create(
            username="technik.hardware",
            defaults={
                "first_name": "Martin",
                "last_name": "Kovář",
                "email": "martin.kovar@example.cz",
                "role": User.ROLE_TECHNICIAN,
            },
        )
        network_tech, _ = User.objects.get_or_create(
            username="technik.sitar",
            defaults={
                "first_name": "Tomáš",
                "last_name": "Němec",
                "email": "tomas.nemec@example.cz",
                "role": User.ROLE_TECHNICIAN,
            },
        )
        if not hardware_tech.password.startswith("pbkdf2_"):
            hardware_tech.set_password("demo1234")
        hardware_tech.role = User.ROLE_TECHNICIAN
        hardware_tech.save()
        if not network_tech.password.startswith("pbkdf2_"):
            network_tech.set_password("demo1234")
        network_tech.role = User.ROLE_TECHNICIAN
        network_tech.save()
        hardware_tech.specialties.set([hardware, printers])
        network_tech.specialties.set([network, software, security])

        existing_tech = User.objects.filter(username="technik").first()
        if existing_tech:
            existing_tech.role = User.ROLE_TECHNICIAN
            existing_tech.save()
            existing_tech.specialties.set([accounts, software])

        ticket_data = [
            ("Notebook se po spuštění několikrát restartuje", "Notebook Dell ve skladu se restartuje během přihlášení. Problém nastává i bez externích zařízení.", users[0], hardware, Ticket.PRIORITY_HIGH, Ticket.STATUS_IN_PROGRESS, hardware_tech),
            ("Nefunkční připojení k Wi-Fi", "Přenosný počítač se po připojení k síti Wi-Fi nedostane na internet.", users[1], network, Ticket.PRIORITY_NORMAL, Ticket.STATUS_ACCEPTED, network_tech),
            ("Výpadek VPN mimo kancelář", "Dnes od 8:30 nelze navázat VPN spojení z domova.", users[2], network, Ticket.PRIORITY_CRITICAL, Ticket.STATUS_IN_PROGRESS, network_tech),
            ("Nový účet pro nového zaměstnance", "Je potřeba vytvořit účet, elektronickou poštu a přístup do adresáře Finance.", users[0], accounts, Ticket.PRIORITY_NORMAL, Ticket.STATUS_NEW, None),
            ("Tiskárna na skladě tiskne pouze prázdné stránky", "Tiskárna HP LaserJet po výměně toneru vytiskne několik prázdných stránek.", users[1], printers, Ticket.PRIORITY_NORMAL, Ticket.STATUS_PENDING, hardware_tech),
            ("Pomalý Outlook", "Outlook po spuštění načítá poštovní složky několik minut.", users[2], software, Ticket.PRIORITY_LOW, Ticket.STATUS_RESOLVED, network_tech),
            ("Podezřelý e-mail s přiloženým souborem", "Z účtu kolegy přišel e-mail s neznámou přílohou a žádostí o otevření odkazu.", users[0], security, Ticket.PRIORITY_HIGH, Ticket.STATUS_ACCEPTED, network_tech),
            ("Uzamčení administrátorského účtu", "Účet byl po několika neúspěšných pokusech automaticky uzamčen.", users[1], accounts, Ticket.PRIORITY_NORMAL, Ticket.STATUS_CLOSED, existing_tech or hardware_tech),
            ("Potřebná licence pro aplikaci AutoCAD", "Licenci mám pro starý počítač, ale potřebuji ji přesunout na nový notebook.", users[2], software, Ticket.PRIORITY_NORMAL, Ticket.STATUS_RESOLVED, network_tech),
            ("Chybí tiskárna v seznamu zařízení", "Po připojení k síti se tiskárna nezobrazuje ve Windows.", users[0], printers, Ticket.PRIORITY_NORMAL, Ticket.STATUS_IN_PROGRESS, hardware_tech),
        ]

        ticket_objects = []
        for index, (title, description, author, cat, priority, status, assignee) in enumerate(ticket_data):
            ticket, created = Ticket.objects.get_or_create(
                title=title,
                defaults={
                    "description": description,
                    "author": author,
                    "assignee": assignee,
                    "category": cat,
                    "priority": priority,
                    "status": Ticket.STATUS_NEW,
                    "updated_by": assignee or existing_tech or hardware_tech,
                },
            )
            if not created:
                ticket_objects.append(ticket)
                continue

            if status == Ticket.STATUS_ACCEPTED:
                ticket.status = Ticket.STATUS_ACCEPTED
                ticket.updated_by = assignee
                ticket.save()
            elif status == Ticket.STATUS_IN_PROGRESS:
                ticket.status = Ticket.STATUS_ACCEPTED
                ticket.updated_by = assignee
                ticket.save()
                ticket.status = Ticket.STATUS_IN_PROGRESS
                ticket.save()
            elif status == Ticket.STATUS_PENDING:
                ticket.status = Ticket.STATUS_ACCEPTED
                ticket.updated_by = assignee
                ticket.save()
                ticket.status = Ticket.STATUS_IN_PROGRESS
                ticket.save()
                ticket.status = Ticket.STATUS_PENDING
                ticket.save()
            elif status == Ticket.STATUS_RESOLVED:
                ticket.status = Ticket.STATUS_ACCEPTED
                ticket.updated_by = assignee
                ticket.save()
                ticket.status = Ticket.STATUS_IN_PROGRESS
                ticket.save()
                ticket.status = Ticket.STATUS_RESOLVED
                ticket.save()
            elif status == Ticket.STATUS_CLOSED:
                ticket.status = Ticket.STATUS_ACCEPTED
                ticket.updated_by = assignee
                ticket.save()
                ticket.status = Ticket.STATUS_IN_PROGRESS
                ticket.save()
                ticket.status = Ticket.STATUS_RESOLVED
                ticket.save()
                ticket.status = Ticket.STATUS_CLOSED
                ticket.save()

            created_time = now - timedelta(days=10 - index, hours=index)
            Ticket.objects.filter(pk=ticket.pk).update(created_at=created_time, updated_at=created_time)
            ticket_objects.append(ticket)

        comment_pairs = [
            ("Notebook se po spuštění několikrát restartuje", hardware_tech, "Do notebooku jsem se podíval, nyní testuji paměť a diagnostiku SSD.", True),
            ("Notebook se po spuštění několikrát restartuje", users[0], "Po restartu se napoprvé objeví modrá obrazovka a poté se počítač vypne.", False),
            ("Nefunkční připojení k Wi-Fi", network_tech, "Zkontrolovali jsme připojení. Odešlete prosím přesnou chvíli výpadku a umístění počítače.", False),
            ("Výpadek VPN mimo kancelář", network_tech, "Kontrola VPN brány probíhá. Zatím ověřujeme připojení od více poskytovatelů.", True),
            ("Pomalý Outlook", network_tech, "Cache Outlooku byla resetována a oprava zavěšení aplikace byla nasazena.", False),
            ("Podezřelý e-mail s přiloženým souborem", network_tech, "Prosím soubor ani odkaz neotevírejte a ponechte zprávu na serveru.", True),
        ]
        for ticket_title, author, content, internal in comment_pairs:
            ticket = Ticket.objects.filter(title=ticket_title).first()
            if ticket:
                Comment.objects.get_or_create(
                    ticket=ticket,
                    author=author,
                    content=content,
                    defaults={"is_internal": internal},
                )

        resolved_titles = [
            "Pomalý Outlook",
            "Potřebná licence pro aplikaci AutoCAD",
        ]
        for title in resolved_titles:
            ticket = Ticket.objects.filter(title=title).first()
            if ticket:
                TicketFeedback.objects.get_or_create(
                    ticket=ticket,
                    defaults={"rating": 5 if title.startswith("Pomalý") else 4, "comment": "Problém byl vyřešen rychle a technik vše vysvětlil."},
                )
                TicketSolution.objects.get_or_create(
                    ticket=ticket,
                    defaults={
                        "technician": network_tech,
                        "content": "Provedena kontrola instalace, oprava konfigurace a ověření, že problém již nenastává.",
                    },
                )

        article_specs = [
            ("Jak připojit notebook k kancelářské síti", network, "Zkontrolujte, zda je Wi-Fi zapnuté, vyberte správnou síť a použijte svůj firemní účet."),
            ("Reset hesla k uživatelskému účtu", accounts, "Heslo lze resetovat přes požadavek helpdesku. Neuvádějte původní heslo do popisu ticketu."),
            ("Co dělat při podezřelém e-mailu", security, "Nepřipojený odkaz nebo přílohu neotevírejte. Předat zprávu správci bezpečnosti a neodpovídat odesílateli."),
            ("Instalace tiskárny ve Windows", printers, "Připojte počítač k síti kanceláře, otevřete Nastavení a přidejte tiskárnu ze seznamu dostupných zařízení."),
        ]
        admin = User.objects.filter(role=User.ROLE_ADMIN).order_by("pk").first()
        for title, cat, content in article_specs:
            KnowledgeArticle.objects.get_or_create(
                slug=slugify(title, allow_unicode=False),
                defaults={
                    "title": title,
                    "content": content,
                    "category": cat,
                    "created_by": admin or hardware_tech,
                    "is_published": True,
                },
            )

        for ticket in Ticket.objects.all()[:6]:
            Notification.objects.get_or_create(
                recipient=ticket.assignee or hardware_tech,
                ticket=ticket,
                message="Byl vytvořen nebo aktualizován požadavek.",
            )

        self.stdout.write(self.style.SUCCESS("Demo data byla připravena."))
        self.stdout.write("Demo účty: jana.novakova / petr.dvorak / lucie.svoboda / technik.sitar / technik.hardware")
        self.stdout.write("Heslo nových demo účtů: demo1234")
