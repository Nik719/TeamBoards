# Management command: seeds 12 KB entries; idempotent — safe to run multiple times
from django.core.management.base import BaseCommand
from api.models import KBEntry


KB_ENTRIES = [
    {
        "question": "What is select_related in Django ORM?",
        "answer": (
            "select_related performs a SQL JOIN and fetches related objects in a single query. "
            "It is used for ForeignKey and OneToOneField relationships to avoid the N+1 query problem. "
            "Example: Book.objects.select_related('author').all() fetches all books and their authors in one SQL query."
        ),
        "category": KBEntry.Category.DATABASE,
    },
    {
        "question": "How does transaction.atomic() work in Django?",
        "answer": (
            "transaction.atomic() creates a database savepoint. All database operations inside the block "
            "are wrapped in a single transaction. If an exception is raised, the entire block rolls back. "
            "If the block completes successfully, the transaction is committed. "
            "It can be used as a decorator or a context manager."
        ),
        "category": KBEntry.Category.DATABASE,
    },
    {
        "question": "What is a JWT token and how does it work?",
        "answer": (
            "A JSON Web Token (JWT) is a compact, URL-safe means of representing claims between two parties. "
            "It consists of three parts: Header (algorithm), Payload (claims/data), and Signature. "
            "The server signs the token with a secret key. The client sends the token in the Authorization header "
            "as 'Bearer <token>'. The server verifies the signature without hitting the database."
        ),
        "category": KBEntry.Category.API,
    },
    {
        "question": "When should I use Q objects in Django?",
        "answer": (
            "Q objects allow you to build complex queries with OR, AND, and NOT logic. "
            "Use them when you need: OR conditions (Q(field=val1) | Q(field=val2)), "
            "NOT conditions (~Q(field=val)), or dynamically built filters. "
            "Example: Entry.objects.filter(Q(question__icontains='jwt') | Q(answer__icontains='jwt'))."
        ),
        "category": KBEntry.Category.DATABASE,
    },
    {
        "question": "What is a REST API and what are its core principles?",
        "answer": (
            "REST (Representational State Transfer) is an architectural style for APIs. "
            "Core principles: Stateless (each request contains all needed info), "
            "Client-Server separation, Uniform Interface (consistent URLs and HTTP verbs), "
            "Cacheable responses, Layered System. "
            "HTTP verbs map to operations: GET (read), POST (create), PUT/PATCH (update), DELETE (delete)."
        ),
        "category": KBEntry.Category.API,
    },
    {
        "question": "How do Django signals work?",
        "answer": (
            "Django signals allow decoupled applications to receive notifications when actions occur. "
            "post_save fires after a model's save() method is called. "
            "Use @receiver(post_save, sender=MyModel) to connect a handler. "
            "The 'created' kwarg is True only on INSERT (first save). "
            "instance._state.adding is also True on first creation. "
            "Connect signals in AppConfig.ready() to ensure they register once."
        ),
        "category": KBEntry.Category.FRAMEWORK,
    },
    {
        "question": "What is the difference between SQL JOIN types?",
        "answer": (
            "INNER JOIN returns rows where both tables have matching values. "
            "LEFT JOIN returns all rows from the left table plus matched rows from the right. "
            "RIGHT JOIN is the reverse. FULL OUTER JOIN returns all rows from both tables. "
            "In Django ORM: select_related uses INNER/LEFT JOIN, prefetch_related uses separate queries."
        ),
        "category": KBEntry.Category.DATABASE,
    },
    {
        "question": "What is AWS S3 and when should I use it?",
        "answer": (
            "Amazon S3 (Simple Storage Service) is an object storage service for storing any amount of data. "
            "Use it for: static file hosting, media uploads (images, videos), data backups, "
            "log archival, and serving large files via CDN (CloudFront). "
            "In Django, use django-storages with boto3 to serve media and static files from S3."
        ),
        "category": KBEntry.Category.CLOUD,
    },
    {
        "question": "What is Docker and why use it for development?",
        "answer": (
            "Docker packages an application and its dependencies into a container — a lightweight, "
            "isolated environment that runs consistently everywhere. "
            "Benefits: eliminates 'works on my machine' issues, easy environment setup with docker-compose, "
            "reproducible builds, and simple scaling. "
            "docker-compose orchestrates multiple services (web + database) with a single command."
        ),
        "category": KBEntry.Category.CLOUD,
    },
    {
        "question": "How does Django REST Framework's permission system work?",
        "answer": (
            "DRF checks permissions in order before executing a view. "
            "Built-in classes: IsAuthenticated, IsAdminUser, AllowAny, IsAuthenticatedOrReadOnly. "
            "Custom permissions extend BasePermission and override has_permission(request, view) "
            "and/or has_object_permission(request, view, obj). "
            "Return True to allow, False to deny (returns 403 for authenticated users, 401 for anonymous)."
        ),
        "category": KBEntry.Category.FRAMEWORK,
    },
    {
        "question": "What is database indexing and when should I add an index?",
        "answer": (
            "A database index is a data structure that speeds up data retrieval at the cost of storage and write speed. "
            "Add indexes on columns you frequently filter, sort, or join on. "
            "In Django: use db_index=True on model fields or Meta.indexes. "
            "Avoid over-indexing — each index slows INSERT/UPDATE. "
            "Use EXPLAIN ANALYZE in PostgreSQL to find slow queries needing indexes."
        ),
        "category": KBEntry.Category.DATABASE,
    },
    {
        "question": "What is the difference between authentication and authorization?",
        "answer": (
            "Authentication verifies *who* you are (e.g., validating a JWT token or password). "
            "Authorization determines *what* you can do (e.g., checking if your role is 'admin'). "
            "In TeamBoard: JWT authentication identifies the company; "
            "the IsAdminUser permission class then authorizes access to admin-only endpoints."
        ),
        "category": KBEntry.Category.API,
    },
]


class Command(BaseCommand):
    help = "Seed the database with sample KBEntry records."

    def handle(self, *args, **kwargs):
        if KBEntry.objects.exists():
            self.stdout.write(self.style.WARNING("KB entries already exist. Skipping seed."))
            return

        entries = [KBEntry(**entry) for entry in KB_ENTRIES]
        KBEntry.objects.bulk_create(entries)

        self.stdout.write(
            self.style.SUCCESS(f"Successfully seeded {len(entries)} KB entries.")
        )
