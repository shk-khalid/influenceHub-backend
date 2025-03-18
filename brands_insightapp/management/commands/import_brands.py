import csv
import ast
from decimal import Decimal
import traceback

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from brands_insightapp.models import (
    Brand, ValuationHistory, Competitor, GenderDemographic,
    BrandsSocialStats, BrandPost
)


def parse_gender_str(gender_str):
    """
    Example parser for a string like:
      "Male: 51.79%, Female: 48.21%"
    Adjust as needed for your CSV format.
    """
    parts = [p.strip() for p in gender_str.split(',')]
    male_val = 0.0
    female_val = 0.0

    for part in parts:
        if 'Male:' in part:
            male_val = float(part.replace('Male:', '').replace('%', '').strip())
        elif 'Female:' in part:
            female_val = float(part.replace('Female:', '').replace('%', '').strip())

    return male_val, female_val


class Command(BaseCommand):
    help = "Import brand data from a CSV file, then set competitors last."

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help="Path to the CSV file.")

    @transaction.atomic
    def handle(self, *args, **options):
        csv_file_path = options['csv_file']

        try:
            with open(csv_file_path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                # STEP 1: Create/update brand data, store competitor info for later
                brand_objs = {}           # brand_id -> Brand object
                brand_name_map = {}       # brand_name -> Brand object (assuming unique brand names)
                brand_competitors = {}    # brand_id -> list of competitor names

                row_count = 0

                for row in reader:
                    row_count += 1

                    try:
                        # 1) BRAND: create or update
                        brand_uuid = row['brand_id']  # Must match your CSV column
                        brand_name = row['brand_name'].strip()
                        location = row['location_state_country'].strip()
                        sector = row['sector_automobile_electronics_cosmetics_fashion'].lower().strip()
                        rating = Decimal(row['brand_rating']) if row['brand_rating'] else Decimal('0.0')

                        # Growth and market performance
                        growth_percentage = Decimal(row['avg_growth_rate'] or '0.0')
                        market_share = Decimal(row['market_performance'] or '0.0')

                        # "value2024" as your Brand.recent_valuation
                        recent_valuation = Decimal(row['value2024']) if row['value2024'] else None

                        brand_obj, _ = Brand.objects.update_or_create(
                            id=brand_uuid,  # Use CSV's UUID
                            defaults={
                                'name': brand_name,
                                'sector': sector if sector in ['electronics','cosmetics','automobile','fashion'] else 'fashion',
                                'location': location,
                                'overall_rating': rating,
                                'market_share': market_share,
                                'growth_percentage': growth_percentage,
                                'recent_valuation': recent_valuation,
                                'instagram_handle': row.get('insta_id', '')
                            }
                        )
                        brand_objs[brand_uuid] = brand_obj
                        brand_name_map[brand_name] = brand_obj

                        # 2) VALUATION HISTORY (2020-2024)
                        for year in [2020, 2021, 2022, 2023, 2024]:
                            col_name = f'value{year}'
                            if row.get(col_name):
                                try:
                                    val = Decimal(row[col_name])
                                    ValuationHistory.objects.update_or_create(
                                        brand=brand_obj,
                                        year=year,
                                        defaults={'valuation': val}
                                    )
                                except (ValueError, Decimal.InvalidOperation):
                                    self.stdout.write(self.style.WARNING(
                                        f"Row {row_count} - Invalid {col_name} value for brand {brand_name}."
                                    ))

                        # 3) GENDER DEMOGRAPHICS
                        gender_str = row.get('gender_male_and_female_', '')
                        if gender_str:
                            male_val, female_val = parse_gender_str(gender_str)
                            GenderDemographic.objects.update_or_create(
                                brand=brand_obj,
                                defaults={
                                    'male_percentage': male_val,
                                    'female_percentage': female_val
                                }
                            )

                        # 4) SOCIAL STATS
                        is_verified = (row.get('is_verified', '').strip().lower() == 'true')

                        # Parse highest_post JSON from CSV
                        highest_post_str = row.get('highest_post', '')
                        try:
                            highest_post_data = ast.literal_eval(highest_post_str) if highest_post_str else {}
                        except Exception as exc:
                            self.stdout.write(self.style.ERROR(
                                f"Row {row_count} - Error parsing highest_post for brand {brand_name}: {exc}"
                            ))
                            highest_post_data = {}

                        bss, _ = BrandsSocialStats.objects.update_or_create(
                            brand=brand_obj,
                            defaults={
                                'username': row.get('username', ''),
                                'bio': row.get('bio', ''),
                                'is_verified': is_verified,
                                'followers': int(float(row.get('followers', 0))),
                                'followings': int(float(row.get('following', 0))),
                                'post_count': int(float(row.get('posts_count', 0))),
                                'follower_ratio': Decimal(row.get('follower_ratio', '0')),
                                'engagement_score': Decimal(row.get('engagement_score', '0')),
                                'engagement_per_follower': Decimal(row.get('engagement_per_follower', '0')),
                                'estimated_reach': Decimal(row.get('estimated_reach', '0')),
                                'estimated_impression': Decimal(row.get('estimated_impression', '0')),
                                'reach_ratio': Decimal(row.get('reach_ratio', '0')),
                                'avg_likes_computed': Decimal(row.get('avg_likes_computed', '0')),
                                'avg_comments_computed': Decimal(row.get('avg_comments_computed', '0')),
                                'avg_views': Decimal(row.get('avg_views', '0')),
                                'highest_post': highest_post_data  # <--- store highest_post as JSON
                            }
                        )

                        # 5) BRAND POSTS (post1..post12) stored as JSON in BrandPost.post_detail
                        for i in range(1, 13):
                            col_name = f'post{i}'
                            if row.get(col_name):
                                try:
                                    post_data = ast.literal_eval(row[col_name])
                                    BrandPost.objects.update_or_create(
                                        insta_stats=bss,
                                        post_number=i,
                                        defaults={'post_detail': post_data}
                                    )
                                except Exception as exc:
                                    self.stdout.write(self.style.ERROR(
                                        f"Row {row_count} - Error parsing {col_name} for brand {brand_name}: {exc}"
                                    ))

                        # 6) Collect competitor data (but do NOT create them yet)
                        competitor_str = row.get('competitor_atleast_3_to_4', '')
                        if competitor_str:
                            try:
                                competitor_list = ast.literal_eval(competitor_str)
                                if isinstance(competitor_list, list):
                                    brand_competitors[brand_uuid] = competitor_list
                            except Exception as exc:
                                self.stdout.write(self.style.ERROR(
                                    f"Row {row_count} - Error parsing competitor list for {brand_name}: {exc}"
                                ))

                    except Exception as exc:
                        # Provide a detailed error message for this specific row
                        tb = traceback.format_exc()
                        raise CommandError(
                            f"An error occurred on row {row_count} (brand: {row.get('brand_name', 'Unknown')})\n"
                            f"Error: {exc}\n\nTraceback:\n{tb}"
                        )

                self.stdout.write(self.style.SUCCESS(
                    f"STEP 1: Imported/updated {row_count} brands from {csv_file_path}.\n"
                    f"Now creating competitor relationships..."
                ))

                # STEP 2: Create competitor records last
                for brand_uuid, comp_list in brand_competitors.items():
                    brand_obj = brand_objs.get(brand_uuid)
                    if not brand_obj:
                        continue

                    for comp_name in comp_list:
                        comp_name = comp_name.strip()
                        # Attempt to find competitor brand by name
                        competitor_brand = brand_name_map.get(comp_name)
                        if competitor_brand is None:
                            self.stdout.write(self.style.WARNING(
                                f"Competitor brand '{comp_name}' not found in brand_name_map."
                            ))
                            continue

                        Competitor.objects.update_or_create(
                            brand=brand_obj,
                            competitor=competitor_brand,
                            defaults={}
                        )

                self.stdout.write(self.style.SUCCESS("STEP 2: Competitors created successfully!"))

        except FileNotFoundError:
            raise CommandError(f"File '{csv_file_path}' does not exist.")
        except Exception as e:
            tb = traceback.format_exc()
            raise CommandError(f"An error occurred while importing data: {e}\n\nTraceback:\n{tb}")
