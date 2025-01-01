import pandas as pd
from django.core.management.base import BaseCommand
from brands_insightapp.models import Brand, Competitor, GenderDemographic, ValuationHistory, BrandSentiment, PerformanceMetric

class Command(BaseCommand):
    help = "Import brand data from an Excel file"

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the Excel file')

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']

        try:
            # Read the Excel file
            data = pd.read_excel(file_path)

            # Iterate through rows in the DataFrame
            for _, row in data.iterrows():
                # Create or update the brand
                brand, created = Brand.objects.update_or_create(
                    name=row['Brand Name'],
                    defaults={
                        'sector': row['Sector (automobile, electronics, cosmetics, fashion)'].lower(),
                        'location': row['Location (state, Country)'],
                        'overall_rating': row['Brand Rating'],
                        'market_share': row['Market Share'],
                        'growth_percentage': row['Growth Percentage'],
                        'recent_valuation': row['Value(2024)'],
                    }
                )

                # Create or update performance metrics (market_share and growth_rate)
                performance_metrics, created = PerformanceMetric.objects.update_or_create(
                    brand=brand,
                    defaults={
                        'market_share': row['Market Share'],
                        'growth_rate': row['Growth Percentage'],
                    }
                )

                # Handle competitors (assuming it's a comma-separated list of competitors)
                competitors = row['Competitor (atleast 3 to 4)'].split(',')
                for comp_name in competitors:
                    Competitor.objects.update_or_create(
                        brand=brand,
                        competitor_name=comp_name.strip(),
                        defaults={'sector': row['Sector (automobile, electronics, cosmetics, fashion)'].lower(), 'market_share': 0.0},
                    )

                # Gender demographics (assuming male, female, and other percentage columns are available)
                gender_data = row['Gender (male & female )']
                male_percentage = female_percentage = other_percentage = 0.0

                # Process gender demographics if the field is not empty
                if isinstance(gender_data, str):
                    gender_data = gender_data.split(',')
                    for data in gender_data:
                        if 'male' in data.lower():
                            male_percentage = float(data.split(':')[1].replace('%', '').strip())
                        elif 'female' in data.lower():
                            female_percentage = float(data.split(':')[1].replace('%', '').strip())
                        else:
                            # Assume other gender if it's not male or female
                            other_percentage = float(data.split(':')[1].replace('%', '').strip())
                
                gender_demo, created = GenderDemographic.objects.update_or_create(
                    brand=brand,
                    defaults={
                        'male_percentage': male_percentage,
                        'female_percentage': female_percentage,
                        'other_percentage': other_percentage,
                    }
                )

                # Insert valuation history
                for year in [2020, 2021, 2022, 2023, 2024]:
                    valuation_column = 'Value({year})'.format(year=year)
                    valuation = row.get(valuation_column)
                    if valuation:
                        ValuationHistory.objects.update_or_create(
                            brand=brand,
                            year=year,
                            defaults={'valuation': valuation}
                        )

                # Brand Sentiment (Handle comments and key mentions)
                comments = row.get('Comments', '[]')  # Default to empty list if no comments field exists
                sentiment, created = BrandSentiment.objects.update_or_create(
                    brand=brand,
                    defaults={
                        'comments': comments,  # Assuming comments are a string or JSON field
                        'key_mentions': row.get('Key Mentions', ''),
                    }
                )

            self.stdout.write(self.style.SUCCESS('Successfully imported brand data!'))

        except Exception as e:
            self.stderr.write(self.style.ERROR("Error importing data: {}".format(str(e))))
