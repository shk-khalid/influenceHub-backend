from django.core.management.base import BaseCommand
from brands_insightapp.models import Brand
from collections import Counter

class Command(BaseCommand):
    help = "Find and list duplicated brands by name"

    def handle(self, *args, **kwargs):
        # Query all brand names from the database
        brand_names = Brand.objects.values_list('name', flat=True)

        # Count the occurrences of each brand name
        name_counts = Counter(brand_names)

        # Find duplicated brands (those with more than 1 occurrence)
        duplicates = {name: count for name, count in name_counts.items() if count > 1}

        if duplicates:
            self.stdout.write(self.style.SUCCESS("Duplicated brands found:"))
            for name, count in duplicates.items():
                self.stdout.write("Brand: {}, Count: {}".format(name, count))
        else:
            self.stdout.write(self.style.SUCCESS("No duplicated brands found."))
