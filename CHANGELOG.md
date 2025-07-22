# Changelog

All notable changes to the Company Leave Management System will be documented in this file.

## [2.0.0] - 2025-07-21

### 🎉 Major Features Added

#### Date Range Support
- **Multi-day Claims & Applications**: Support for consecutive work periods and leave applications up to 14 days
- **Holiday Period Management**: Perfect for Easter weekends, Christmas week, and other consecutive periods
- **Smart Date Validation**: Prevents overlapping periods and ensures logical date ranges

#### Enhanced User Interface
- **Real-time Credit Calculation**: Dynamic display showing days count and credits as you type
- **Days Counter**: Prominent display of number of days (1, 2, 3, etc.) in forms and history
- **5-Column Layout**: Start Date | End Date | Session | Days & Credits | Event/Project
- **Interactive Forms**: Live updates when changing dates or sessions

#### Credit System Improvements
- **Automatic Calculation**: Credits = Session Value × Number of Days
- **Session Types**:
  - AM Session: 0.5 credits per day
  - PM Session: 0.5 credits per day  
  - Full Day: 1.0 credits per day
- **Balance Validation**: Real-time checking of sufficient credits for leave applications

#### Database Enhancements
- **New Fields**: `work_end_date` and `leave_end_date` for date ranges
- **Model Methods**: `get_work_days_count()` and `get_leave_days_count()` for automatic calculation
- **Data Migration**: Migration 0011 adds date range support while preserving existing data

### 🔧 Technical Improvements

#### Frontend Enhancements
- **JavaScript Integration**: Real-time form calculations without page refresh
- **Bootstrap Components**: Enhanced badges, cards, and responsive layouts
- **Dynamic Content**: Credits display updates as "X credits × Y days"
- **Error Handling**: Comprehensive form validation with helpful error messages

#### Backend Optimizations
- **Form Validation**: Enhanced validation for date ranges and credit balance
- **Model Logic**: Improved save methods with automatic credit calculation
- **Query Optimization**: Efficient database queries for balance calculations

#### User Experience
- **Visual Feedback**: Color-coded badges for status, days, and credits
- **Intuitive Design**: Clear labels and helpful text for all form fields
- **History Tables**: Enhanced tables showing date ranges and days count
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile

### 📋 Detailed Changes

#### Models (models.py)
- Added `work_end_date` field to SpecialWorkClaim model
- Added `leave_end_date` field to SpecialLeaveApplication model
- Implemented `get_work_days_count()` method for day calculation
- Implemented `get_leave_days_count()` method for day calculation
- Enhanced `save()` methods with automatic credit calculation for date ranges

#### Forms (forms.py)
- Added end date fields to both claim and application forms
- Implemented comprehensive date range validation
- Added overlap detection to prevent conflicting periods
- Enhanced clean methods with 14-day maximum validation
- Added helpful error messages for validation failures

#### Views (views.py)
- Updated context to include balance information
- Enhanced error handling for form submissions
- Improved pagination for history tables
- Added validation for credit sufficiency

#### Templates
- **special_work_claim.html**: 
  - Added days counter and credit display
  - Implemented 5-column responsive layout
  - Added JavaScript for real-time calculations
  - Enhanced history table with date ranges
  
- **special_leave_apply.html**:
  - Added days counter and credit display
  - Implemented balance checking display
  - Added JavaScript for real-time calculations
  - Enhanced history table with date ranges

#### Database Migration
- **Migration 0011**: Added date range fields with proper defaults
- **Data Preservation**: All existing records maintained during upgrade
- **Backward Compatibility**: Single-day functionality preserved

### 🎯 Use Cases Supported

#### Work Claims
- **Single Day Overtime**: Traditional single-day work claims
- **Weekend Projects**: 2-3 day weekend work periods
- **Holiday Coverage**: Working during Easter, Christmas, etc.
- **Extended Projects**: Up to 14 consecutive work days

#### Leave Applications  
- **Personal Days**: Single day special leave
- **Long Weekends**: 3-4 day extended breaks
- **Holiday Periods**: Using earned credits for consecutive days off
- **Vacation Extensions**: Combining with annual leave for longer breaks

### 🔍 Examples

#### 3-Day Easter Work Claim
- **Dates**: Apr 18-20, 2025 (Friday to Sunday)
- **Session**: Full Day
- **Days**: 3
- **Credits Earned**: 3.0 (1.0 × 3 days)

#### Christmas Week Leave Application  
- **Dates**: Dec 23-27, 2025 (5 consecutive days)
- **Session**: AM (Half days)
- **Days**: 5
- **Credits Required**: 2.5 (0.5 × 5 days)

### 📊 System Metrics
- **Maximum Period**: 14 consecutive days
- **Credit Precision**: 0.5 credit increments
- **Validation Rules**: 5+ comprehensive validation checks
- **UI Updates**: Real-time calculation without page refresh
- **Database Efficiency**: Optimized queries for balance calculations

---

## [1.0.0] - 2025-07-15

### Initial Release
- Basic special work claim functionality
- Simple leave application system
- Manager approval workflow
- Employee authentication
- SQLite database support
- Bootstrap UI framework
- Basic reporting features

### Core Features
- Single-day work claims
- Single-day leave applications
- Credit balance tracking
- Manager dashboard
- Employee profiles
- Public holiday management

---

**Note**: This project follows [Semantic Versioning](https://semver.org/)
