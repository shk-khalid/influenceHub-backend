import pandas as pd
from decimal import Decimal, InvalidOperation

def debug_decimal_conversion(file_path):
    # Read the Excel file
    data = pd.read_excel(file_path)

    # Iterate through rows in the DataFrame and check values being converted to Decimal
    for _, row in data.iterrows():
        try:
            # Check and convert each value to Decimal and print the value
            for column in ['Brand Rating', 'Market Share', 'Growth Percentage', 'Value(2024)', 'Value(2023)', 'Value(2022)', 'Value(2021)', 'Value(2020)']:
                value = row[column]
                if pd.notna(value):  # Only process if value is not NaN
                    # Try to convert to Decimal and print the result
                    try:
                        print("Converting column: {}, value: {}".format(column, value))
                        Decimal(value)
                    except InvalidOperation as e:
                        print("Invalid decimal conversion for {} with value: {}".format(column, value))
                        raise e
        except Exception as e:
            print("Error in row: {}, {}".format(row, e))

# Call the debug function with your file path
debug_decimal_conversion(r'C:\project\influenceHub\BrandData.xlsx')
