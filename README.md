# Django Base Project Template

A comprehensive Django 5 base project template with PostgreSQL database, Docker support, and production-ready configuration (optimized for Railway deployment). 
This template provides a solid foundation for building Django applications with modern best practices.

## Features

- **Django 5.0+** with Python 3.11+
- **Modular Settings** - Separated settings for development, staging, and production
- **Database Support** - PostgreSQL database
- **Docker Ready** - Complete Docker and Docker Compose configuration
- **Authentication** - Built-in user authentication with login/logout
- **Modern UI** - Bootstrap-styled responsive templates
- **Static Files** - WhiteNoise for static file serving
- **Production Ready** - Security settings and Gunicorn WSGI server
- **Environment Management** - Comprehensive environment variable configuration
- **Development Tools** - Ready for debugging and testing

## Quick Start

### Docker Development Setup


1. **Copy environment file:**
```powershell
Copy-Item env.example .env
```

2. **Build and start containers:**
```powershell
docker-compose build
docker-compose up
```

3. **Run initial migrations:**
```powershell
docker-compose run --rm django python manage.py migrate
docker-compose run --rm django python manage.py createsuperuser
```

4. **Access the application:**
   - Application: http://localhost:8000
   - PostgreSQL: localhost:5433 (mapped from container port 5432)

## Project Structure

```
django-base/
├── config/                 # Django project configuration
│   ├── settings/          # Split settings for different environments
│   │   ├── __init__.py
│   │   ├── base.py        # Common settings shared across environments
│   │   ├── local.py       # Development settings
│   │   └── prod.py        # Production settings
│   ├── __init__.py
│   ├── asgi.py           # ASGI configuration
│   ├── urls.py           # Main URL configuration
│   └── wsgi.py           # WSGI configuration
├── core/                   # Main application (rename as needed)
│   ├── __init__.py
│   ├── admin.py          # Django admin configuration
│   ├── apps.py           # App configuration
│   ├── models.py         # Database models
│   ├── tests.py          # Test cases
│   ├── urls.py           # App URL patterns
│   └── views.py          # View functions/classes
├── templates/              # HTML templates
│   ├── base.html         # Base template with Bootstrap
│   ├── core/
│   │   └── home.html     # Home page template
│   └── registration/
│       └── login.html    # Login page template
├── static/                 # Static files (CSS, JS, images)
├── media/                  # User uploaded files
├── docker-compose.yml      # Docker Compose configuration
├── Dockerfile              # Docker image definition
├── requirements.txt        # Python dependencies
├── env.example             # Environment variables template
├── .gitignore             # Git ignore rules
├── manage.py              # Django management script
└── README.md              # This file
```

## Environment Variables

Copy `env.example` to `.env` and configure:

### Required Variables
- `SECRET_KEY`: Django secret key (change in production)
- `DEBUG`: Enable/disable debug mode
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`: Database credentials
- `DB_HOST`, `DB_PORT`: Database connection

### Optional Variables
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts (production)
- `DJANGO_SUPERUSER_*`: Automatic superuser creation (for Railway deployment)

## Database Configuration

The project supports two database configuration methods:

### Railway Deployment (Production)

Railway automatically provides a `DATABASE_URL` environment variable when you add a PostgreSQL service. The project automatically detects and uses this:

1. **Add PostgreSQL service** in Railway dashboard
2. **Click "Connect"** - Railway automatically sets `DATABASE_URL`
3. **No manual configuration needed!** The project automatically uses `DATABASE_URL`

The `DATABASE_URL` format: `postgresql://user:password@host:port/dbname`

### Local Development (Docker)

For local development, use individual database variables in your `.env` file:

```env
DB_NAME=myproject
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db  # Use 'db' for Docker Compose (service name)
DB_PORT=5432
```

**Note:** The project automatically detects which method to use:
- If `DATABASE_URL` exists → uses Railway/Heroku style connection
- Otherwise → falls back to individual variables for local development

## Available Commands

### Django Management Commands (with Docker)
```bash
# All Django commands must be run inside the container
docker-compose run --rm django python manage.py migrate
docker-compose run --rm django python manage.py createsuperuser
docker-compose run --rm django python manage.py makemigrations
docker-compose run --rm django python manage.py collectstatic
docker-compose run --rm django python manage.py test
```

**Note:** The `--rm` flag automatically removes the container after the command completes.

## Production Deployment

### Railway Deployment (Optimized)

This project is **optimized for Railway deployment**. You can deploy it directly without any changes:

1. **Connect your repository to Railway**
2. **Set environment variables** in Railway dashboard:
   - `DJANGO_SETTINGS_MODULE=config.settings.prod`
   - `SECRET_KEY` (generate a strong secret key)
   - `DEBUG=False`
   - `ALLOWED_HOSTS` (your Railway domain)
   - **Database**: Just create a PostgreSQL service and click "Connect" - Railway automatically sets `DATABASE_URL` (no manual variables needed!)
   - `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD` (optional)

3. **Media Files Storage** (for user uploads):
   
   **Option 1: Railway Volume (Recommended for small quantities)**
   - In Railway dashboard, go to your service → "Volumes" tab
   - Click "Add Volume" and mount it to `/app/media` in your service
   - This is super easy and perfect for small to medium file quantities
   - Files persist across deployments
   
   **Option 2: Cloud Storage Bucket (For larger scale)**
   - Use AWS S3, Google Cloud Storage, or similar
   - Configure `DEFAULT_FILE_STORAGE` in `config/settings/prod.py`
   - More complex setup but better for production at scale

4. **Deploy!** Railway will:
   - Build the Docker image using the `Dockerfile`
   - Run `start.sh` which automatically:
     - Runs migrations
     - Creates superuser (if configured)
     - Collects static files
     - Starts the server with Gunicorn

**No manual setup required!** The `start.sh` script handles everything automatically.


## Security Features

The production settings include:

- Secure cookies (HTTPS only)
- HSTS headers
- Content type nosniff
- XSS protection
- Secure referrer policy
- X-Frame-Options protection
- CSRF protection

## Authentication

- Login URL: `/accounts/login/`
- Logout URL: `/accounts/logout/`
- Home page: `/` (requires authentication)

Default redirects:
- After login: home page
- After logout: login page

## Development

### Adding New Apps
1. Create the app: `docker-compose run --rm django python manage.py startapp appname`
2. Add to `INSTALLED_APPS` in `config/settings/base.py`
3. Include URLs in `config/urls.py`
4. Create templates in `templates/appname/` directory

### Database Migrations
```bash
docker-compose run --rm django python manage.py makemigrations
docker-compose run --rm django python manage.py migrate
```

### Running Tests
```bash
docker-compose run --rm django python manage.py test
docker-compose run --rm django python manage.py test core  # Test specific app
```

## Troubleshooting

### Common Issues

1. **PostgreSQL connection errors:**
   - Ensure PostgreSQL is running
   - Check database credentials in `.env`
   - For Docker: ensure `db` service is up

2. **Static files not loading:**
   - Run `docker-compose run --rm django python manage.py collectstatic`
   - Check `STATIC_URL` and `STATIC_ROOT` settings

3. **Docker build errors:**
   - Check Docker is running
   - Verify Dockerfile syntax
   - Try `docker system prune` to clean up

### Getting Help

- Check Django documentation: https://docs.djangoproject.com/
- Review error logs in the console
- Use Django's built-in error pages in development mode

## Customization

This template is designed to be easily customizable:

- **Project Name**: Update folder names, database names, and references
- **Apps**: Add new Django apps as needed for your project
- **Templates**: Modify the Bootstrap-based templates to match your design
- **Settings**: Add environment-specific configurations

## License

This Django base project template is provided for educational and development purposes. Feel free to use it as a starting point for your own Django projects.
