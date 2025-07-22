from django.core.management.base import BaseCommand
from leave.models import PublicHoliday
import holidays
from datetime import datetime


class Command(BaseCommand):
    help = 'Import holidays for specified regions and years'
    
    def add_arguments(self, parser):
        parser.add_argument('--regions', nargs='+', default=['HK', 'CN'], 
                          help='Regions to import holidays for (HK, CN)')
        parser.add_argument('--years', nargs='+', type=int, 
                          default=[datetime.now().year], 
                          help='Years to import holidays for')
        parser.add_argument('--force', action='store_true',
                          help='Force reimport even if holidays exist')
    
    def handle(self, *args, **options):
        regions = options['regions']
        years = options['years']
        force = options['force']
        
        for region in regions:
            for year in years:
                self.stdout.write(f'Importing holidays for {region} {year}...')
                
                # Check if holidays already exist
                existing_count = PublicHoliday.objects.filter(
                    region=region, year=year
                ).count()
                
                if existing_count > 0 and not force:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  Holidays for {region} {year} already exist ({existing_count} holidays). '
                            'Use --force to reimport.'
                        )
                    )
                    continue
                
                if force and existing_count > 0:
                    # Delete existing holidays
                    PublicHoliday.objects.filter(
                        region=region, year=year
                    ).delete()
                    self.stdout.write(f'  Deleted {existing_count} existing holidays')
                
                try:
                    # Get holidays from the holidays library
                    if region == 'HK':
                        region_holidays = holidays.HongKong(years=year)
                    elif region == 'CN':
                        region_holidays = holidays.China(years=year)
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'  Unknown region: {region}')
                        )
                        continue
                    
                    # Import holidays
                    imported_count = 0
                    for date, name in region_holidays.items():
                        PublicHoliday.objects.get_or_create(
                            name=name,
                            date=date,
                            region=region,
                            year=year,
                            defaults={
                                'is_active': True,
                                'is_imported': True
                            }
                        )
                        imported_count += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  Successfully imported {imported_count} holidays for {region} {year}'
                        )
                    )
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  Error importing holidays for {region} {year}: {e}')
                    )
        
        self.stdout.write(self.style.SUCCESS('Holiday import completed!'))
