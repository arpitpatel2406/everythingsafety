import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Initialize the project with default data and setup'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin-email',
            type=str,
            default='admin@everythingsafety.com',
            help='Email for the admin user',
        )
        parser.add_argument(
            '--admin-password',
            type=str,
            default='admin123',
            help='Password for the admin user',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Initializing EverythingSafety project...')
        )

        # Run migrations
        self.stdout.write('📦 Running migrations...')
        call_command('migrate', verbosity=0)

        # Create superuser if it doesn't exist
        User = get_user_model()
        admin_email = options['admin_email']
        admin_password = options['admin_password']

        if not User.objects.filter(email=admin_email).exists():
            self.stdout.write('👤 Creating superuser...')
            User.objects.create_superuser(
                username='admin',
                email=admin_email,
                password=admin_password
            )
            self.stdout.write(
                self.style.SUCCESS(f'✅ Superuser created with email: {admin_email}')
            )
        else:
            self.stdout.write('👤 Superuser already exists')

        # Collect static files
        self.stdout.write('📁 Collecting static files...')
        call_command('collectstatic', verbosity=0, interactive=False)

        # Create logs directory if it doesn't exist
        logs_dir = 'logs'
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
            self.stdout.write(f'📝 Created {logs_dir} directory')

        self.stdout.write(
            self.style.SUCCESS(
                '🎉 Project initialization complete!\n'
                f'Admin login: {admin_email}\n'
                f'Admin password: {admin_password}\n'
                'You can now run: python manage.py runserver'
            )
        )
