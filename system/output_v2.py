import pandas as pd
import os

def process_journals_data(mode="加和"):
    """
    处理journals数据，根据tag标签统计STLCs和EU27，并包含其他指定国家
    
    参数:
        mode: "加和" 或 "平均"
            - "加和": STLCs和EU27使用加和方式计算
            - "平均": STLCs和EU27使用平均值方式计算
    """
    # 文件路径
    tag_file = "/Users/xiaokong/temp_work/2026/pdq/UN193_with_tag.xlsx"
    journals_file = "/Users/xiaokong/temp_work/2026/pdq/excel/IPRI.xlsx"
    
    # 根据mode设置输出文件名
    base_output_file = "/Users/xiaokong/temp_work/2026/pdq/excel/IPRI_v2.xlsx"
    if mode == "平均":
        # 如果文件名包含_v2，替换为_v2_平均，否则添加_平均
        if base_output_file.endswith("_v2.xlsx"):
            output_file = base_output_file.replace("_v2.xlsx", "_v2_平均.xlsx")
        else:
            output_file = base_output_file.replace(".xlsx", "_平均.xlsx")
    else:
        output_file = base_output_file
    
    # 检查文件是否存在
    if not os.path.exists(tag_file):
        raise FileNotFoundError(f"文件不存在: {tag_file}")
    if not os.path.exists(journals_file):
        raise FileNotFoundError(f"文件不存在: {journals_file}")
    
    # 1. 读取tag文件，获取country和tag的映射
    print("正在读取tag文件...")
    df_tag = pd.read_excel(tag_file)
    
    # 检查必要的列是否存在
    if 'country' not in df_tag.columns:
        raise ValueError(f"tag文件中缺少'country'列。可用列: {df_tag.columns.tolist()}")
    if 'tag' not in df_tag.columns:
        raise ValueError(f"tag文件中缺少'tag'列。可用列: {df_tag.columns.tolist()}")
    
    # 创建tag映射：country -> tag
    country_to_tag = {}
    for _, row in df_tag.iterrows():
        country = str(row['country']).strip()
        tag = str(row['tag']).strip()
        country_to_tag[country] = tag
    
    # 获取STLCs和EU的国家列表
    stlcs_countries = [country for country, tag in country_to_tag.items() if tag == 'STLCs']
    eu_countries = [country for country, tag in country_to_tag.items() if tag == 'EU']
    
    print(f"STLCs国家数量: {len(stlcs_countries)}")
    print(f"EU国家数量: {len(eu_countries)}")
    
    # 2. 读取journals文件
    print("正在读取journals文件...")
    df_journals = pd.read_excel(journals_file)
    
    # 检查第一列是否为year
    if df_journals.columns[0].lower() != 'year':
        raise ValueError(f"journals文件第一列应为'year'，实际为: {df_journals.columns[0]}")
    
    # 设置year为索引，方便处理
    df_journals = df_journals.set_index('year')
    
    # 获取所有可用的国家列名
    available_countries = df_journals.columns.tolist()
    print(f"journals文件中可用的国家列: {available_countries[:10]}...")  # 只显示前10个
    
    # 3. 准备输出数据
    result_data = {'year': df_journals.index.tolist()}
    
    # 需要统计的地区
    target_regions = ['STLCs', 'EU27', 'China', 'Germany', 'India', 'Japan', 'Russia', 'United Kingdom', 'United States']
    
    # 验证mode参数
    if mode not in ["加和", "平均"]:
        raise ValueError(f"mode参数必须是'加和'或'平均'，当前为: {mode}")
    
    print(f"使用模式: {mode}")
    
    # 4. 统计STLCs
    print(f"正在统计STLCs (模式: {mode})...")
    stlcs_values = []
    for year in df_journals.index:
        valid_values = []
        for country in stlcs_countries:
            if country in df_journals.columns:
                value = df_journals.loc[year, country]
                if pd.notna(value):
                    try:
                        valid_values.append(float(value))
                    except (ValueError, TypeError):
                        pass
        
        if mode == "加和":
            stlcs_values.append(sum(valid_values) if valid_values else 0)
        else:  # mode == "平均"
            stlcs_values.append(sum(valid_values) / len(valid_values) if valid_values else 0)
    
    result_data['STLCs'] = stlcs_values
    
    # 5. 统计EU27
    print(f"正在统计EU27 (模式: {mode})...")
    eu27_values = []
    for year in df_journals.index:
        valid_values = []
        for country in eu_countries:
            if country in df_journals.columns:
                value = df_journals.loc[year, country]
                if pd.notna(value):
                    try:
                        valid_values.append(float(value))
                    except (ValueError, TypeError):
                        pass
        
        if mode == "加和":
            eu27_values.append(sum(valid_values) if valid_values else 0)
        else:  # mode == "平均"
            eu27_values.append(sum(valid_values) / len(valid_values) if valid_values else 0)
    
    result_data['EU27'] = eu27_values
    
    # 6. 直接获取其他国家的数据
    print("正在获取其他国家数据...")
    direct_countries = {
        'China': 'China',
        'Germany': 'Germany',
        'India': 'India',
        'Japan': 'Japan',
        'Russia': 'Russia',
        'United Kingdom': 'United Kingdom',
        'United States': 'United States'
    }
    
    for region_name, country_name in direct_countries.items():
        if country_name in df_journals.columns:
            result_data[region_name] = df_journals[country_name].tolist()
            print(f"  ✓ {region_name}: {country_name}")
        else:
            # 尝试模糊匹配
            matched = False
            for col in df_journals.columns:
                if country_name.lower() in str(col).lower() or str(col).lower() in country_name.lower():
                    result_data[region_name] = df_journals[col].tolist()
                    print(f"  ✓ {region_name}: {country_name} (匹配到: {col})")
                    matched = True
                    break
            if not matched:
                # 如果找不到，填充为0
                result_data[region_name] = [0] * len(df_journals.index)
                print(f"  ✗ {region_name}: {country_name} (未找到，填充为0)")
    
    # 7. 创建结果DataFrame
    result_df = pd.DataFrame(result_data)
    
    # 确保列的顺序
    column_order = ['year'] + [r for r in target_regions if r in result_df.columns]
    result_df = result_df[column_order]
    
    # 8. 保存到Excel文件
    print(f"\n正在保存结果到: {output_file}")
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    result_df.to_excel(output_file, index=False)
    print(f"✓ 成功保存！共 {len(result_df)} 行数据")
    print(f"\n结果预览:")
    print(result_df.head(10))
    
    return result_df

if __name__ == "__main__":
    import sys
    
    # 从命令行参数获取mode，默认为"加和"
    mode = "加和"
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    
    try:
        result = process_journals_data(mode=mode)
        print("\n处理完成！")
    except Exception as e:
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()

