import pandas as pd
from decimal import Decimal, InvalidOperation

# Load the dataset
file_path = r'C:\project\influenceHub\BrandData.xlsx'
sheet_data = pd.read_excel(file_path, sheet_name='Sheet1')

# Function to convert values to Decimal
def convert_to_decimal(value):
    try:
        # Attempt to convert to Decimal
        return Decimal(value)
    except (InvalidOperation, ValueError, TypeError):
        # If conversion fails, return NaN or handle as required
        return None

# List of columns to convert to Decimal
decimal_columns = ['Brand Rating', 'Value(2024)', 'Value(2023)', 'Value(2022)', 'Value(2021)', 'Value(2020)', 
                   'Growth Percentage', 'Market Share']

# Apply the conversion to each specified column
for column in decimal_columns:
    if column in sheet_data.columns:
        sheet_data[column] = sheet_data[column].apply(convert_to_decimal)

# Check and save the updated data
output_file_path = r'C:\project\influenceHub\BrandData.xlsx'
sheet_data.to_excel(output_file_path, index=False)
print("Data successfully cleaned and saved to {}".format(output_file_path))
