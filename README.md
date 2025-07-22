# Company Leave Management System

A comprehensive Django-based leave management system with special work claims and leave applications functionality.

## 🚀 Features

### Core Functionality
- **Employee Authentication**: Secure login system with custom authentication backends
- **Leave Balance Management**: Track earned and used special leave credits
- **Special Work Claims**: Submit claims for overtime/weekend work to earn leave credits
- **Special Leave Applications**: Apply for special leave using earned credits
- **Manager Approval Workflow**: Complete approval process with notifications
- **Date Range Support**: Handle single-day and multi-day periods (up to 14 consecutive days)

### Advanced Features
- **Real-time Credit Calculation**: Dynamic calculation of credits based on session and days
- **Date Range Validation**: Prevent overlapping claims and applications
- **Holiday Period Support**: Perfect for consecutive days during Easter, Christmas, etc.
- **Responsive Design**: Bootstrap-based UI that works on all devices
- **Comprehensive History**: Track all claims and applications with detailed status

## 📋 System Requirements

- Python 3.8+
- Django 4.2+
- SQLite (development) / PostgreSQL (production)
- Bootstrap 4.6
- Font Awesome 5.15

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd company-leave-system
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Setup
```bash
cp env.example .env
# Edit .env file with your database and secret key settings
```

### 5. Database Migration
```bash
python manage.py migrate
```

### 6. Create Superuser
```bash
python manage.py createsuperuser
```

### 7. Run Development Server
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000` to access the application.

## 📖 Usage Guide

### Special Work Claims
1. Navigate to **Special Work Claim** page
2. Select work date (start date for multi-day periods)
3. Optionally select end date for consecutive work days
4. Choose session: AM (0.5 credits), PM (0.5 credits), or Full Day (1.0 credits)
5. Enter event/project name and description
6. Set priority level
7. Submit for manager approval

**Credit Calculation Examples:**
- Single full day: 1.0 credit
- 3-day Easter weekend (full days): 3.0 credits
- 5-day Christmas week (AM sessions): 2.5 credits

### Special Leave Applications
1. Navigate to **Apply Special Leave** page
2. Check your available credit balance
3. Select leave date (start date for multi-day periods)
4. Optionally select end date for consecutive leave days
5. Choose session type
6. Enter reason and urgency level
7. System automatically calculates required credits
8. Submit if you have sufficient balance

### Manager Dashboard
- View pending claims and applications
- Approve or reject with comments
- Track team leave balances
- Generate reports

## 🎯 Key Features Details

### Date Range Support
- **Single Day**: Leave end date blank
- **Multi-Day**: Set end date for consecutive periods
- **Maximum**: Up to 14 consecutive days per claim/application
- **Validation**: Prevents overlapping periods and ensures sufficient balance

### Credit System
- **Earning Credits**: Work beyond normal hours to earn special leave credits
- **Using Credits**: Apply for special leave using earned credits
- **Sessions**:
  - AM (9:00-13:00): 0.5 credits per day
  - PM (13:00-18:00): 0.5 credits per day
  - Full Day (9:00-18:00): 1.0 credits per day

### Real-time Calculations
- Dynamic days count display
- Automatic credit calculation
- Live balance checking
- Form validation with helpful error messages

## 🗂️ Project Structure

```
company-leave-system/
├── leave/                          # Main application
│   ├── models.py                   # Database models
│   ├── views.py                    # Application views
│   ├── forms.py                    # Django forms
│   ├── urls.py                     # URL routing
│   ├── admin.py                    # Admin interface
│   ├── templates/leave/            # HTML templates
│   ├── management/commands/        # Custom Django commands
│   └── migrations/                 # Database migrations
├── leave_system/                   # Project settings
│   ├── settings.py                 # Django settings
│   ├── urls.py                     # Main URL configuration
│   └── wsgi.py                     # WSGI configuration
├── requirements.txt                # Python dependencies
├── manage.py                       # Django management script
└── README.md                       # This file
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file based on `env.example`:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Database Settings
- **Development**: SQLite (default)
- **Production**: PostgreSQL recommended

## 📊 Database Models

### Core Models
- **EmployeeProfile**: User profile with region and department info
- **LeaveBalance**: Track special leave credits by year
- **SpecialWorkClaim**: Work claims to earn credits
- **SpecialLeaveApplication**: Leave applications using credits
- **PublicHoliday**: Holiday calendar management

### Workflow Models
- **SpecialLeaveNotification**: System notifications
- **SpecialLeaveApprovalWorkflow**: Approval process tracking
- **EmployeeImportRecord**: Bulk employee import tracking

## 🎨 UI Components

### Dashboard Features
- Credit balance summary cards
- Quick action buttons
- Recent activity feed
- Status indicators with color coding

### Form Features
- Real-time credit calculation
- Date range validation
- Dynamic days counter
- Session-based credit display

### Table Features
- Sortable columns
- Pagination support
- Status badges
- Date range display

## 🧪 Testing

### Run Tests
```bash
python manage.py test
```

### Test Coverage
- Model validation tests
- Form validation tests
- View functionality tests
- Authentication tests

## 🚀 Deployment

### Production Checklist
1. Set `DEBUG=False` in settings
2. Configure production database
3. Set up static file serving
4. Configure email settings for notifications
5. Set up SSL certificate
6. Configure logging

### Recommended Deployment Platforms
- **Heroku**: Easy deployment with PostgreSQL
- **AWS**: EC2 with RDS
- **DigitalOcean**: App Platform or Droplets
- **PythonAnywhere**: Simple Django hosting

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the documentation in the `/docs` folder
- Review the code comments and docstrings

## 🎯 Recent Updates

### Version 2.0 Features
- ✅ Date range support for consecutive days
- ✅ Real-time credit calculation
- ✅ Enhanced UI with dynamic forms
- ✅ Improved validation and error handling
- ✅ Manager approval workflow
- ✅ Comprehensive history tracking

### Upcoming Features
- Email notifications for approvals
- Mobile app API
- Advanced reporting dashboard
- Integration with payroll systems
- Bulk import/export functionality

---

**Built with ❤️ using Django and Bootstrap**
