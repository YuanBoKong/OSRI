import pandas as pd
import os
import re
from pathlib import Path

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

def process_file(file_path):
    """
    处理单个Excel文件，标准化国家名称并合并计数
    """
    print(f"Processing: {file_path}")
    
    # 读取文件
    df = pd.read_excel(file_path)
    
    # 标准化国家名称
    df['Country'] = df['Country'].apply(standardize_country_name)
    
    # 按标准化后的国家名称分组并求和
    result_df = df.groupby('Country', as_index=False)['Count'].sum()
    
    # 按国家名称排序
    result_df = result_df.sort_values('Country').reset_index(drop=True)
    
    # 保存回原文件
    result_df.to_excel(file_path, index=False)
    
    print(f"  ✓ Standardized and saved")
    return result_df

def main():
    # 目标目录
    result_dir = Path('HER/result')
    
    # 获取所有xlsx文件
    xlsx_files = list(result_dir.glob('*.xlsx'))
    
    if not xlsx_files:
        print("No xlsx files found in HER/result directory")
        return
    
    print(f"Found {len(xlsx_files)} xlsx files to process\n")
    
    # 处理每个文件
    for file_path in sorted(xlsx_files):
        try:
            result_df = process_file(file_path)
            print(f"  Total countries: {len(result_df)}, Total count: {result_df['Count'].sum()}\n")
        except Exception as e:
            print(f"  ✗ Error processing {file_path}: {e}\n")
    
    print("All files processed!")

if __name__ == "__main__":
    main()

