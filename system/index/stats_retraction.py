import pandas as pd
from datetime import datetime

# Read the Excel file
print("Reading retraction_watch_2025.xlsx...")
df = pd.read_excel('retraction_watch_2025.xlsx')

# Convert RetractionDate to datetime
df['RetractionDate'] = pd.to_datetime(df['RetractionDate'], errors='coerce')

# Extract year from RetractionDate
df['Year'] = df['RetractionDate'].dt.year

# Task 1: Count retractions by year
print("Counting retractions by year...")
yearly_counts = df['Year'].value_counts().sort_index()
yearly_df = pd.DataFrame({
    'Year': yearly_counts.index,
    'Total_Retractions': yearly_counts.values
})

# Save to total_retraction.xlsx
yearly_df.to_excel('total_retraction.xlsx', index=False)
print(f"Saved total retractions by year to total_retraction.xlsx")
print(f"Total years: {len(yearly_df)}")

# Task 2: Count retractions by country and year
print("\nProcessing countries...")

# Filter out rows with missing Country or Year
df_filtered = df.dropna(subset=['Country', 'Year']).copy()

# Split countries by semicolon and create expanded dataframe
country_year_data = []

for idx, row in df_filtered.iterrows():
    countries = str(row['Country']).split(';')
    year = int(row['Year'])
    
    # Clean each country name (strip whitespace)
    for country in countries:
        country = country.strip()
        if country:  # Only add non-empty countries
            country_year_data.append({
                'Country': country,
                'Year': year
            })

# Create dataframe from expanded data
country_year_df = pd.DataFrame(country_year_data)

# Count by country and year
print("Counting retractions by country and year...")
country_year_counts = country_year_df.groupby(['Country', 'Year']).size().reset_index(name='Count')

# Sort by Country and Year
country_year_counts = country_year_counts.sort_values(['Country', 'Year'])

# Save to country_retraction.xlsx
country_year_counts.to_excel('country_retraction.xlsx', index=False)
print(f"Saved country retractions to country_retraction.xlsx")
print(f"Total country-year combinations: {len(country_year_counts)}")
print(f"Unique countries: {country_year_df['Country'].nunique()}")
print(f"Year range: {country_year_df['Year'].min()} - {country_year_df['Year'].max()}")

print("\nDone!")

