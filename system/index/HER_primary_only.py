import pandas as pd
import re

# Read the Excel file
print("Reading HER/2023_HCR.xlsx...")
df = pd.read_excel('HER/2023_HCR.xlsx')

# Function to extract country from affiliation string
def extract_country(affiliation):
    """
    Extract country from affiliation string.
    Format: "Institution, Country" or "Independent"
    """
    if pd.isna(affiliation) or affiliation == '':
        return None
    
    affiliation = str(affiliation).strip()
    
    # Handle "Independent" case
    if affiliation == 'Independent':
        return 'Independent'
    
    # Extract country after ", "
    if ', ' in affiliation:
        country = affiliation.split(', ')[-1].strip()
        return country if country else None
    
    # If no comma found, return the whole string (might be just country name)
    return affiliation if affiliation else None

# Collect all countries from Primary Affiliation column only
all_countries = []

print("Processing Primary Affiliation column...")
for idx, row in df.iterrows():
    primary_aff = row['Primary Affiliation']
    country = extract_country(primary_aff)
    if country:
        all_countries.append(country)

# Count occurrences of each country
print("Counting countries...")
country_counts = pd.Series(all_countries).value_counts().sort_index()

# Create result dataframe
result_df = pd.DataFrame({
    'Country': country_counts.index,
    'Count': country_counts.values
})

# Sort by country name
result_df = result_df.sort_values('Country')

# Save to Excel file
output_file = 'HER/country_count_2023_HCR_primary_only.xlsx'
result_df.to_excel(output_file, index=False)

print(f"\nSaved country counts to {output_file}")
print(f"Total countries: {len(result_df)}")
print(f"Total affiliations processed: {len(all_countries)}")
print(f"\nTop 10 countries:")
print(result_df.head(10))

print("\nDone!")

