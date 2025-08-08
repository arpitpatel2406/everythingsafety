# EverythingSafety - Django Production Project

A production-ready Django application with PostgreSQL database and comprehensive configuration for deployment.

## Features

- **Django 5.2.5** with production-ready configuration
- **PostgreSQL** database integration
- **Django REST Framework** for API development
- **Environment-based settings** (development, production, testing)
- **Security features** configured for production
- **Static files** handling with WhiteNoise
- **Error tracking** with Sentry integration
- **CORS** support for frontend integration
- **Debug toolbar** for development
- **Comprehensive logging** configuration

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL 12+

### Installation

1. **Clone the repository and set up virtual environment:**
   ```bash
   git clone <your-repo-url>
   cd everythingsafety
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment setup:**
   ```bash
   cp .env.example .env
   # Edit .env with your database and other settings
   ```

4. **Database setup:**
   ```bash
   # Create PostgreSQL database
   createdb everythingsafety_db
   
   # Run migrations
   python manage.py migrate
   
   # Create superuser
   python manage.py createsuperuser
   ```

5. **Collect static files:**
   ```bash
   python manage.py collectstatic
   ```

### Running the Application

#### Development
```bash
# Start Django development server
python manage.py runserver
```

#### Production
```bash
# Use Gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

## Project Structure

```
everythingsafety/
├── apps/                   # Django applications
│   └── core/              # Core application
├── config/                # Project configuration
│   ├── settings/          # Environment-specific settings
│   │   ├── __init__.py
│   │   ├── base.py       # Base settings
│   │   ├── development.py # Development settings
│   │   ├── production.py  # Production settings
│   │   └── testing.py     # Testing settings
│   ├── urls.py           # URL configuration
│   └── wsgi.py           # WSGI configuration
├── static/                # Static files
├── media/                 # User uploaded files
├── templates/             # Django templates
├── logs/                  # Application logs
├── venv/                  # Virtual environment
├── .env                   # Environment variables
├── .env.example          # Environment variables example
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development dependencies
├── manage.py             # Django management script
└── README.md             # This file
```

## Environment Variables

Key environment variables in `.env`:

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_NAME=everythingsafety_db
DATABASE_USER=your_db_user
DATABASE_PASSWORD=your_db_password
DATABASE_HOST=localhost
DATABASE_PORT=5432

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True

# Sentry (optional)
SENTRY_DSN=your-sentry-dsn
```

## Development

### Creating New Apps

```bash
# Create app in apps directory
python manage.py startapp myapp apps/myapp

# Add to INSTALLED_APPS in settings/base.py
LOCAL_APPS = [
    'apps.core',
    'apps.myapp',  # Add your new app
]
```

### Database Operations

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Reset database (development only)
python manage.py flush
```

### Testing

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run tests
python manage.py test

# Run with coverage
pytest --cov=apps --cov-report=html
```

## Deployment

### Production Checklist

1. **Security Settings:**
   - Set `DEBUG=False`
   - Configure `ALLOWED_HOSTS`
   - Set secure `SECRET_KEY`
   - Configure HTTPS settings

2. **Database:**
   - Use production PostgreSQL instance
   - Configure connection pooling
   - Set up database backups

3. **Static/Media Files:**
   - Configure cloud storage (AWS S3) for media files
   - Set up CDN for static files

4. **Monitoring:**
   - Configure Sentry for error tracking
   - Set up application monitoring
   - Configure log aggregation

5. **Performance:**
   - Configure caching if needed
   - Configure load balancing

### Docker Deployment

```dockerfile
# Example Dockerfile structure
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "config.wsgi:application"]
```

## API Documentation

When using Django REST Framework, API documentation is available at:
- Development: http://localhost:8000/api/
- Production: https://yourdomain.com/api/

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

---

**Note:** This is a production-ready Django template. Remember to:
- Change the SECRET_KEY for production
- Configure your database settings
- Set up proper domain names and SSL certificates
- Configure monitoring and logging for production use
