@echo off
echo 🚀 Setting up EverythingSafety Django Project...

REM Change to project directory
cd /d "c:\Users\kavya\Documents\My_programming\everythingsafety"

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install/upgrade packages
echo 📦 Installing packages...
pip install -r requirements.txt

REM Run Django checks
echo 🔍 Checking Django configuration...
python manage.py check --settings=config.settings.development

REM Create database tables
echo 🗃️ Creating database tables...
python manage.py migrate --settings=config.settings.development

REM Collect static files
echo 📁 Collecting static files...
python manage.py collectstatic --noinput --settings=config.settings.development

REM Create superuser (optional)
echo 👤 You can create a superuser by running:
echo python manage.py createsuperuser --settings=config.settings.development

echo.
echo ✅ Setup complete! 
echo.
echo To start the development server:
echo python manage.py runserver --settings=config.settings.development
echo.
echo Admin panel will be available at: http://127.0.0.1:8000/admin/
echo Health check at: http://127.0.0.1:8000/api/health/
echo.
pause
