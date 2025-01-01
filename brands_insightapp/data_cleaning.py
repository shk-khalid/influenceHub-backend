import pandas as pd
import random
import uuid

# Load the Excel file
file_path = r'C:\project\influenceHub\BrandData.xlsx'
data = pd.read_excel(file_path)

# 1. Standardize text columns
text_columns = ['Brand Name', 'Location (state, Country)', 
                'Sector (automobile, electronics, cosmetics, fashion)']
for col in text_columns:
    if col in data.columns:
        data[col] = data[col].str.title()

# 2. Clean Brand Rating column
if 'Brand Rating' in data.columns:
    data['Brand Rating'] = data['Brand Rating'].astype(str).str.replace(r'\.\.', '.', regex=True)
    data['Brand Rating'] = pd.to_numeric(data['Brand Rating'], errors='coerce')

# 3. Convert Value columns to readable format (B for billions, T for trillions)
value_columns = [col for col in data.columns if 'Value' in col]

def convert_to_float(value):
    try:
        if isinstance(value, str):
            if 'B' in value:
                return float(value.replace('B', '').replace('$', '').strip()) * 1e9
            elif 'T' in value:
                return float(value.replace('T', '').replace('$', '').strip()) * 1e12
        return float(value)
    except ValueError:
        return None

for col in value_columns:
    data[col] = data[col].apply(convert_to_float)

# 4. Populate Competitor List by Matching Sector and Valuation
def find_competitors(row, data, tolerance=20):
    sector = row['Sector (automobile, electronics, cosmetics, fashion)']
    valuation = row['Value(2024)']
    if pd.isna(sector) or pd.isna(valuation):
        return []
    valuation_float = convert_to_float(valuation)
    similar_brands = data[
        (data['Sector (automobile, electronics, cosmetics, fashion)'] == sector) &
        (data['Value(2024)'].apply(convert_to_float).between(valuation_float - tolerance, valuation_float + tolerance)) &
        (data['Brand Name'] != row['Brand Name'])
    ]['Brand Name'].unique().tolist()
    return similar_brands[:4]

if 'Competitor (atleat 3 to 4)' in data.columns:
    def ensure_competitor_list(row, data):
        competitors = find_competitors(row, data)
        if len(competitors) < 2:
            additional_brands = data[
                (data['Sector (automobile, electronics, cosmetics, fashion)'] == row['Sector (automobile, electronics, cosmetics, fashion)']) &
                (data['Brand Name'] != row['Brand Name'])
            ]['Brand Name'].unique().tolist()
            competitors.extend([brand for brand in additional_brands if brand not in competitors])
        return competitors[:4]

    data['Competitor (atleat 3 to 4)'] = data.apply(
        lambda row: ensure_competitor_list(row, data) if not isinstance(row['Competitor (atleat 3 to 4)'], list) or len(row['Competitor (atleat 3 to 4)']) < 2 else row['Competitor (atleat 3 to 4)'], 
        axis=1
    )

# 5. Assign Random Gender Percentages
def assign_random_percentages():
    male_percentage = random.uniform(40, 60)
    female_percentage = 100 - male_percentage
    return "Male: {:.2f}%, Female: {:.2f}%".format(male_percentage, female_percentage)

if 'Gender (male & female )' in data.columns:
    data['Gender (male & female )'] = data['Gender (male & female )'].apply(
        lambda x: assign_random_percentages() if pd.isna(x) or "Male" not in str(x) else x
    )

# 6. Validate Social Media Handles
if 'Social media handle (INSTA)' in data.columns:
    data['Social media handle (INSTA)'] = data['Social media handle (INSTA)'].fillna('Unknown')

# 7. Add Random Unique ID for Each Brand
def generate_unique_id():
    return str(uuid.uuid4())

data['Brand ID'] = data.apply(lambda row: generate_unique_id(), axis=1)

# 8. Calculate Growth Percentage (based on past 5 years valuation) and Market Share (randomized based on growth and valuation)
def calculate_growth_percentage(row):
    try:
        # Assuming the 'Value' columns hold valuations for 2020, 2021, 2022, 2023, 2024
        past_valuations = [convert_to_float(row['Value({})'.format(year)]) for year in range(2020, 2025)]
        if None not in past_valuations and len(past_valuations) == 5:
            start_value = past_valuations[0]  # 2020 valuation
            end_value = past_valuations[-1]  # 2024 valuation
            growth_percentage = ((end_value - start_value) / start_value) * 100
            return round(growth_percentage, 2)
        return None
    except Exception:
        return None

def calculate_market_share(row):
    try:
        # Randomly assign a market share, but influenced by the growth percentage and valuation
        valuation = convert_to_float(row['Value(2024)'])
        growth_percentage = row['Growth Percentage']
        
        # Market share formula can be adjusted according to your logic
        if growth_percentage and valuation:
            base_market_share = random.uniform(5, 15)  # Random base value
            adjusted_market_share = base_market_share + (growth_percentage / 100) * (valuation / 1e12)
            return round(min(adjusted_market_share, 100), 2)  # Ensure market share doesn't exceed 100%
        return random.uniform(5, 15)  # Fallback to random value if growth or valuation is missing
    except Exception:
        return random.uniform(5, 15)  # Fallback to random value

# Apply growth and market share calculations
data['Growth Percentage'] = data.apply(calculate_growth_percentage, axis=1)
data['Market Share'] = data.apply(calculate_market_share, axis=1)

# Save the cleaned data to a new file
cleaned_file_path = r'C:\project\influenceHub\Enhanced_BrandData.xlsx'
data.to_excel(cleaned_file_path, index=False)

print("Data cleaned, demographics updated with random gender percentages and unique IDs, and new columns for Growth Percentage and Market Share calculated. Saved to {}.".format(cleaned_file_path))
