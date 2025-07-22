# Setup Guide for New Mac

## Prerequisites

### 1. Install Python 3.8+
```bash
# Check if Python is installed
python3 --version

# If not installed, download from python.org or use Homebrew:
brew install python3
```

### 2. Install Git
```bash
# Check if Git is installed
git --version

# If not installed:
brew install git
```

### 3. Install Homebrew (if not already installed)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## Installation Steps

### Step 1: Clone or Download the Repository

#### Option A: Clone from GitHub (Recommended)
```bash
# Clone the repository
git clone https://github.com/wongivan852/company-leave-system.git
cd company-leave-system
```

#### Option B: Download and Extract
1. Go to https://github.com/wongivan852/company-leave-system
2. Click "Code" → "Download ZIP"
3. Extract the ZIP file
4. Open Terminal and navigate to the extracted folder

### Step 2: Create Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# You should see (venv) in your terminal prompt
```

### Step 3: Install Dependencies
```bash
# Install required packages
pip install -r requirements.txt
```

### Step 4: Database Setup
```bash
# Apply database migrations
python manage.py migrate

# Create superuser (admin account)
python manage.py createsuperuser
# Follow the prompts to set username, email, and password
```

### Step 5: Load Sample Data (Optional)
```bash
# Import sample employees
python manage.py import_employees sample_employees.csv

# Import public holidays
python manage.py import_holidays
```

### Step 6: Run the Application
```bash
# Start the development server
python manage.py runserver

# The application will be available at:
# http://127.0.0.1:8000
```

## Configuration

### Environment Variables
1. Copy the example environment file:
```bash
cp env.example .env
```

2. Edit `.env` file with your settings:
```
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
```

### Admin Access
- URL: http://127.0.0.1:8000/admin/
- Use the superuser credentials you created in Step 4

### Regular User Access
- URL: http://127.0.0.1:8000/
- Login with employee credentials or create new employees via admin panel

## Features Available

### Core Leave Management
- ✅ Apply for annual leave
- ✅ View leave balance
- ✅ Track application status
- ✅ Manager approval workflow

### Special Leave Features
- ✅ Apply for special leave (overtime compensation)
- ✅ Special work claims (Saturday work)
- ✅ Date range support for multi-day applications
- ✅ Credit system for special leave balance

### Administrative Features
- ✅ Employee management
- ✅ Holiday calendar management
- ✅ Leave balance tracking
- ✅ Import/export functionality

## Troubleshooting

### Common Issues

#### 1. Permission Errors
```bash
# If you get permission errors, try:
sudo chown -R $(whoami) /path/to/company-leave-system
```

#### 2. Python Version Issues
```bash
# Make sure you're using Python 3.8+
python3 --version

# If using older version, install Python 3.8+
brew install python@3.8
```

#### 3. Virtual Environment Issues
```bash
# Deactivate current environment
deactivate

# Remove old environment
rm -rf venv

# Create new environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 4. Database Issues
```bash
# Reset database (WARNING: This deletes all data)
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

### Port Already in Use
```bash
# If port 8000 is in use, try a different port:
python manage.py runserver 8001
```

## File Structure
```
company-leave-system/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── db.sqlite3               # Database file (created after migration)
├── leave_system/            # Main project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── leave/                   # Main application
│   ├── models.py           # Database models
│   ├── views.py            # Application logic
│   ├── forms.py            # Form definitions
│   ├── admin.py            # Admin interface
│   ├── templates/          # HTML templates
│   └── migrations/         # Database migrations
├── sample_employees.csv     # Sample data for testing
└── README.md               # Project documentation
```

## Next Steps
1. Access the application at http://127.0.0.1:8000
2. Login to admin panel to configure employees and settings
3. Test the leave application process
4. Import your actual employee data
5. Configure public holidays for your region

## Support
- Check the README.md for detailed feature documentation
- Review CHANGELOG.md for version history
- See DEPLOYMENT.md for production deployment guide
