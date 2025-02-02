import pandas as pd

# Load the Excel file
file_path = r'C:\project\influenceHub\BrandData.xlsx'  # Replace with your file path
data = pd.ExcelFile(file_path)

# Parse the first sheet
data_frame = data.parse(data.sheet_names[0])

# Define numeric columns to validate and clean
numeric_columns = [
    'Brand Rating', 'Value(2024)', 'Value(2023)', 'Value(2022)',
    'Value(2021)', 'Value(2020)', 'Growth Percentage', 'Market Share'
]

# Convert numeric columns to appropriate types and handle errors
for col in numeric_columns:
    data_frame[col] = pd.to_numeric(data_frame[col], errors='coerce')

# Fill missing numeric values with 0 or a placeholder (optional)
data_frame[numeric_columns] = data_frame[numeric_columns].fillna(0)

# Remove any leading or trailing spaces in object columns
object_columns = data_frame.select_dtypes(include=['object']).columns
data_frame[object_columns] = data_frame[object_columns].apply(lambda x: x.str.strip())

# Save the cleaned data to a CSV file
output_path = r'C:\project\influenceHub\Cleaned_BrandData.csv'
data_frame.to_csv(output_path, index=False)

print("Preprocessed data saved to {}".format(output_path))
