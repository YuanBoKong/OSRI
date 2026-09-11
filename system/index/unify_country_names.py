import pandas as pd
import re

def standardize_country_name(country_name):
    """
    标准化国家名称
    """
    if pd.isna(country_name):
        return country_name
    
    country = str(country_name).strip()
    
    # 1. China相关 -> "China"
    if re.search(r'china', country, re.IGNORECASE):
        return "China"
    
    # 2. Korea相关
    # 北朝鲜（North Korea, Democratic People's Republic of Korea） -> "Democratic People's Republic of Korea"
    # 南朝鲜（South Korea, Korea等其他变体） -> "Republic of Korea"
    if re.search(r'korea', country, re.IGNORECASE):
        # 检查是否是北朝鲜
        if 'Democratic People\'s Republic of Korea' in country or 'North Korea' in country:
            return "Democratic People's Republic of Korea"  # 北朝鲜统一为Democratic People's Republic of Korea
        else:
            # 其他Korea变体（如South Korea, Korea等）统一为Republic of Korea（南朝鲜）
            return "Republic of Korea"
    
    # 3. USA相关 -> "USA"
    usa_patterns = [
        r'^usa$',
        r'^united states$',
        r'^united states of america$',
        r'^the united states of america$',
        r'^america$',
        r'^united state$'
    ]
    for pattern in usa_patterns:
        if re.match(pattern, country, re.IGNORECASE):
            return "USA"
    
    # 4. UK相关 -> "UK"
    uk_patterns = [
        r'^uk$',
        r'^united kingdom$',
        r'^britain$',
        r'^england$',
        r'^great britain$'
    ]
    for pattern in uk_patterns:
        if re.match(pattern, country, re.IGNORECASE):
            return "UK"
    
    return country

# 读取Excel文件
input_file = 'results/1. 每个国家每年撤稿量.xlsx'
print(f"Reading {input_file}...")
df = pd.read_excel(input_file)

print(f"Original shape: {df.shape}")

# 标准化Country列的国家名称
print("Standardizing country names...")
df['Country'] = df['Country'].apply(standardize_country_name)

# 保存回原文件
print(f"Saving to {input_file}...")
df.to_excel(input_file, index=False)

print(f"✓ Country names standardized and saved!")
print(f"Final shape: {df.shape}")
print("\nDone!")

