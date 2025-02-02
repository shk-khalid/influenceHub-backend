import os
import pandas as pd
from django.core.management.base import BaseCommand
from brands_insightapp.models import (
    Brand, Competitor, GenderDemographic, ValuationHistory,
    BrandSentiment, PerformanceMetric
)

class Command(BaseCommand):
    help = "Import brand data from a file (CSV or Excel format)"

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the file (CSV or Excel)')

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']

        # Ensure the file exists
        if not os.path.exists(file_path):
            self.stderr.write(self.style.ERROR("File not found: {}".format(file_path)))
            return

        # Determine file extension and read the file accordingly
        file_extension = os.path.splitext(file_path)[-1].lower()
        try:
            if file_extension == '.csv':
                data = pd.read_csv(file_path)
            elif file_extension in ['.xls', '.xlsx']:
                data = pd.read_excel(file_path, engine='openpyxl')
            else:
                self.stderr.write(self.style.ERROR("Unsupported file format. Please provide a CSV or Excel file."))
                return
        except Exception as e:
            self.stderr.write(self.style.ERROR("Failed to read the file. Error: {}".format(str(e))))
            return

        # Validate data columns
        required_columns = [
            'Brand Name', 'Sector (automobile, electronics, cosmetics, fashion)',
            'Location (state, Country)', 'Brand Rating', 'Market Share',
            'Growth Percentage', 'Value(2024)', 'Competitor (atleast 3 to 4)',
            'Gender (male & female )', 'Social media handle (INSTA)'
        ]
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            self.stderr.write(self.style.ERROR("Missing columns in the file: {}".format(', '.join(missing_columns))))
            return

        # Process the data row by row
        for _, row in data.iterrows():
            try:
                # Create or update the brand
                brand, created = Brand.objects.get_or_create(
                    id=row['Brand ID'],
                    defaults={
                        'name': row['Brand Name'],
                        'location': row['Location (state, Country)'],
                        'sector': row['Sector (automobile, electronics, cosmetics, fashion)'].lower(),
                        'overall_rating': float(row['Brand Rating']),
                        'market_share': float(row['Market Share']),
                        'growth_percentage': float(row['Growth Percentage']),
                        'recent_valuation': float(row['Value(2024)']),
                        'instagram_handle': row['Social media handle (INSTA)'],
                    }
                )

                if created:
                    self.stdout.write(self.style.SUCCESS(f"Created brand: {brand.name}"))

                # Create or update performance metrics
                PerformanceMetric.objects.update_or_create(
                    brand=brand,
                    defaults={
                        'market_share': row['Market Share'],
                        'growth_rate': row['Growth Percentage'],
                    }
                )

                # Handle competitors
                competitors = eval(row['Competitor (atleast 3 to 4)'])
                for comp_name in competitors:
                    Competitor.objects.update_or_create(
                        brand=brand,
                        competitor_name=comp_name.strip(),
                    )

                # Handle gender demographics
                gender_data = row['Gender (male & female )']
                male_percentage = 0.0
                if isinstance(gender_data, str):
                    gender_data = gender_data.split(',')
                    for data in gender_data:
                        if 'male' in data.lower():
                            male_percentage = float(data.split(':')[1].replace('%', '').strip())

                female_percentage = 100 - male_percentage
                
                GenderDemographic.objects.update_or_create(
                    brand=brand,
                    defaults={
                        'male_percentage': male_percentage,
                        'female_percentage': female_percentage,
                    }
                )


                # Insert valuation history
                for year in [2020, 2021, 2022, 2023, 2024]:
                    valuation_column = 'Value({})'.format(year)
                    valuation = row.get(valuation_column, None)
                    if pd.notna(valuation):
                        ValuationHistory.objects.update_or_create(
                            brand=brand,
                            year=year,
                            defaults={'valuation': valuation}
                        )

                """ # Handle brand sentiment
                comments = row.get('Comments', '[]')
                BrandSentiment.objects.update_or_create(
                    brand=brand,
                    defaults={
                        'comments': comments,
                        'key_mentions': row.get('Key Mentions', ''),
                    }
                ) """

            except Exception as e:
                self.stderr.write(self.style.ERROR("Error processing row {}: {}".format(row['Brand Name'], str(e))))

        self.stdout.write(self.style.SUCCESS("Successfully imported brand data!"))
