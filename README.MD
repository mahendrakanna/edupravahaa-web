# EduPravahaa Web
 
This is the admin backend for the EduPravahaa platform, built with Python and Django to manage administrative tasks.
 
## Prerequisites
- Python 3.8+
- Git
- pip
- Optional: Docker (for `docker-compose.yml`)
 
## Setup and Running Instructions
 
1. **Clone the Repository**
   ```bash
   git clone https://github.com/DIDeccan/edupravahaa_admin.git
   cd edupravahaa_admin
   ```
 
2. **Navigate to Backend**
   ```bash
   cd Backend
   ```
 
3. **Create and Activate Virtual Environment**
   ```bash
   python -m venv edu_venv
   ```
   - Windows: `.\edu_venv\Scripts\activate`
   - macOS/Linux: `source edu_venv/bin/activate`
 
4. **Go to dist Directory**
   ```bash
   cd dist
   ```
 
5. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install setuptools
   ```
 
6. **Set Environment Variables**
   - Windows: `$env:ENV_FILE=".env.local"`
   - macOS/Linux: `export ENV_FILE=".env.local"`
   - Ensure `.env.local` exists with:
   - Copy .env.example and enter you creds for db,twilio etc.
   - make sure to add <EMAIL_PORT="587">.
 
7. **Apply Database Migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
 
8. **Start the Server**
   ```bash
   python manage.py runserver
   ```
   Access at `http://localhost:8000`. Create a superuser with `python manage.py createsuperuser` if needed.
 
## Project Structure
```
edupravahaa_admin/
├── Backend/                # Django project files
│   ├── dist/              # Contains manage.py, requirements.txt
│   │   ├── manage.py
│   │   ├── requirements.txt
│   │   └── .env.example   # Environment example config
│   │   └── .env.local     # Environment config (not in Git)
├── edu_venv/              # Virtual environment (not in Git)
├── Frontend/              # React project files
├── docker-compose.yml     # Optional Docker setup
├── .gitignore
└── README.md
```
 
## Contributing
1. Fork the repo.
2. Create a branch: `git checkout -b feature/your-feature`
3. Commit: `git commit -m "Add feature"`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request.