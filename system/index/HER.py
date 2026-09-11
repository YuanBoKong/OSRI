import pandas as pd
import re

# Read the Excel file
print("Reading HER/2014_HCR.xlsx...")
df = pd.read_excel('HER/2014_HCR.xlsx')

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

# Collect all countries from both columns
# If Primary and Secondary are from the same country, count only once
all_countries = []

print("Processing affiliations (same country in Primary and Secondary counts only once)...")
for idx, row in df.iterrows():
    primary_aff = row['Primary Affiliation']
    secondary_aff = row['Secondary Affiliations']
    
    primary_country = extract_country(primary_aff)
    secondary_country = extract_country(secondary_aff)
    
    # If both countries exist and are the same, count only once
    if primary_country and secondary_country:
        if primary_country == secondary_country:
            all_countries.append(primary_country)
        else:
            # Different countries, count both
            all_countries.append(primary_country)
            all_countries.append(secondary_country)
    elif primary_country:
        # Only primary country exists
        all_countries.append(primary_country)
    elif secondary_country:
        # Only secondary country exists
        all_countries.append(secondary_country)

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
output_file = 'HER/country_count_2014_HCR（需进一步确认合并）.xlsx'
result_df.to_excel(output_file, index=False)

print(f"\nSaved country counts to {output_file}")
print(f"Total countries: {len(result_df)}")
print(f"Total affiliations processed: {len(all_countries)}")
print(f"\nTop 10 countries:")
print(result_df.head(10))

print("\nDone!")

