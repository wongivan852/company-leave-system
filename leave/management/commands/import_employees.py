from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from leave.models import Employee, LeaveType
from datetime import datetime
import csv


class Command(BaseCommand):
    help = 'Import employee data from CSV file'
    
    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to CSV file')
        parser.add_argument('--update', action='store_true',
                          help='Update existing employees')
        parser.add_argument('--dry-run', action='store_true',
                          help='Show what would be imported without making changes')
    
    def handle(self, *args, **options):
        csv_file = options['csv_file']
        update = options['update']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                
                created_count = 0
                updated_count = 0
                error_count = 0
                
                for row_num, row in enumerate(csv_reader, start=2):
                    try:
                        # Required fields
                        username = row.get('username', '').strip()
                        email = row.get('email', '').strip()
                        first_name = row.get('first_name', '').strip()
                        last_name = row.get('last_name', '').strip()
                        date_joined = row.get('date_joined', '').strip()
                        region = row.get('region', 'HK').strip()
                        company = row.get('company', 'Krystal Institute Ltd').strip()
                        
                        # Optional fields
                        is_staff = row.get('is_staff', 'False').strip().lower() in ('true', '1', 'yes')
                        annual_leave_balance = row.get('annual_leave_balance', '0').strip()
                        sick_leave_balance = row.get('sick_leave_balance', '0').strip()
                        
                        if not all([username, email, first_name, last_name, date_joined]):
                            self.stdout.write(
                                self.style.ERROR(f'Row {row_num}: Missing required fields')
                            )
                            error_count += 1
                            continue
                        
                        # Parse date
                        try:
                            join_date = datetime.strptime(date_joined, '%Y-%m-%d').date()
                        except ValueError:
                            try:
                                join_date = datetime.strptime(date_joined, '%d/%m/%Y').date()
                            except ValueError:
                                self.stdout.write(
                                    self.style.ERROR(
                                        f'Row {row_num}: Invalid date format. Use YYYY-MM-DD or DD/MM/YYYY'
                                    )
                                )
                                error_count += 1
                                continue
                        
                        if dry_run:
                            self.stdout.write(f'Would process: {username} ({first_name} {last_name})')
                            continue
                        
                        # Create or update user
                        user, user_created = User.objects.get_or_create(
                            username=username,
                            defaults={
                                'email': email,
                                'first_name': first_name,
                                'last_name': last_name,
                                'is_staff': is_staff
                            }
                        )
                        
                        if not user_created and update:
                            # Update existing user
                            user.email = email
                            user.first_name = first_name
                            user.last_name = last_name
                            user.is_staff = is_staff
                            user.save()
                            updated_count += 1
                        elif user_created:
                            created_count += 1
                        elif not user_created and not update:
                            self.stdout.write(
                                self.style.WARNING(f'Row {row_num}: User {username} exists (use --update to update)')
                            )
                            continue
                        
                        # Create or update employee profile
                        valid_companies = ['Krystal Institute Ltd', 'Krystal Technology Ltd', 'Other']
                        company_value = company if company in valid_companies else 'Krystal Institute Ltd'
                        
                        # Generate employee ID
                        employee_id = f"EMP{user.id:04d}"
                        
                        profile, profile_created = Employee.objects.get_or_create(
                            user=user,
                            defaults={
                                'employee_id': employee_id,
                                'department': 'To Be Assigned',
                                'position': 'To Be Assigned',
                                'date_joined': join_date,
                                'region': region if region in ['HK', 'CN'] else 'HK',
                                'company': company_value
                            }
                        )
                        
                        if not profile_created and update:
                            profile.date_joined = join_date
                            profile.region = region if region in ['HK', 'CN'] else 'HK'
                            profile.company = company_value
                            if not profile.employee_id:
                                profile.employee_id = employee_id
                            profile.save()
                        
                        # Note: Leave balance functionality not implemented yet
                        # This would require a LeaveBalance model to be created
                        if annual_leave_balance or sick_leave_balance:
                            self.stdout.write(
                                self.style.WARNING(f'Row {row_num}: Leave balance import skipped (LeaveBalance model not implemented)')
                            )
                                
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'Row {row_num}: Error processing - {str(e)}')
                        )
                        error_count += 1
                        continue
                
                # Summary
                if not dry_run:
                    if created_count > 0:
                        self.stdout.write(
                            self.style.SUCCESS(f'Created {created_count} employees')
                        )
                    if updated_count > 0:
                        self.stdout.write(
                            self.style.SUCCESS(f'Updated {updated_count} employees')
                        )
                    if error_count > 0:
                        self.stdout.write(
                            self.style.WARNING(f'{error_count} rows had errors')
                        )
                    
                    self.stdout.write(self.style.SUCCESS('Employee import completed!'))
                else:
                    self.stdout.write(self.style.SUCCESS('Dry run completed'))
                
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File not found: {csv_file}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error reading file: {e}'))
