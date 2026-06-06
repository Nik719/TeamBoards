# Management command: creates an admin user + sets company role to admin in one step
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from api.models import Company


class Command(BaseCommand):
    help = "Create a TeamBoard admin user in one step."

    def add_arguments(self, parser):
        parser.add_argument('--username',     required=True)
        parser.add_argument('--password',     required=True)
        parser.add_argument('--email',        default='')
        parser.add_argument('--company-name', default='')

    def handle(self, *args, **options):
        username     = options['username']
        password     = options['password']
        email        = options['email']
        company_name = options['company_name'] or username

        if User.objects.filter(username=username).exists():
            raise CommandError(f"User '{username}' already exists.")

        user    = User.objects.create_user(username=username, password=password, email=email)
        company = user.company
        company.company_name = company_name
        company.role         = Company.Role.ADMIN
        company.save(update_fields=['company_name', 'role'])

        self.stdout.write(self.style.SUCCESS(
            f"Admin created  →  username: {username}  |  api_key: {company.api_key}"
        ))
