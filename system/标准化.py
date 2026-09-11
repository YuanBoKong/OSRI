import pandas as pd
import os
import numpy as np

def normalize_data(input_file, output_file=None, coefficient=1.25):
    """
    标准化数据：使用公式 S_Platform(t) = coefficient × ln(N_Repo(c, t) + 1) / ln(N_Repo^max(t) + 1)
    对每一行（每年），使用该年的最大值进行标准化
    
    参数:
        input_file: 输入Excel文件路径
        output_file: 输出Excel文件路径，如果为None，则自动生成
        coefficient: 系数，默认为1.25
    
    返回:
        标准化后的DataFrame
    """
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"文件不存在: {input_file}")
    
    # 读取Excel文件
    print(f"正在读取文件: {input_file}")
    df = pd.read_excel(input_file)
    
    # 检查第一列是否为year
    first_col = df.columns[0]
    if first_col.lower() != 'year':
        print(f"警告: 第一列不是'year'，而是'{first_col}'，将作为索引列处理")
    
    # 设置year为索引（如果第一列是year）
    if first_col.lower() == 'year':
        df = df.set_index('year')
    else:
        # 如果不是year，保持原样，但第一列不参与标准化
        df = df.set_index(first_col)
    
    # 获取需要标准化的列（除了索引列之外的所有列）
    numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
    
    print(f"找到 {len(numeric_columns)} 个数值列需要标准化")
    print(f"列名: {numeric_columns}")
    
    # 创建标准化后的DataFrame副本
    df_normalized = df.copy()
    
    # 对每一行（每年）进行标准化：使用公式 S = coefficient × ln(N + 1) / ln(N_max + 1)
    def normalize_row(row):
        row_values = row[numeric_columns]
        row_max = row_values.max()
        
        # 如果最大值是NaN或0，跳过该行
        if pd.isna(row_max) or row_max == 0:
            normalized_values = pd.Series([0.0] * len(numeric_columns), index=numeric_columns)
        else:
            # 公式：coefficient × ln(N_Repo(c, t) + 1) / ln(N_Repo^max(t) + 1)
            # 对于每个单元格：ln(值 + 1) / ln(该年最大值 + 1) × coefficient
            normalized_values = (np.log1p(row_values) / np.log1p(row_max)) * coefficient
            normalized_values = normalized_values.fillna(0.0)
        
        return normalized_values
    
    df_normalized[numeric_columns] = df.apply(normalize_row, axis=1)
    
    print(f"按行标准化完成，使用公式: S = {coefficient} × ln(N + 1) / ln(N_max + 1)")
    
    # 重置索引，将year列恢复为普通列
    df_normalized = df_normalized.reset_index()
    
    # 如果输出文件路径未指定，自动生成
    if output_file is None:
        # 在输入文件名基础上添加_标准化后缀
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}_标准化.xlsx"
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 保存到Excel文件
    print(f"\n正在保存标准化结果到: {output_file}")
    df_normalized.to_excel(output_file, index=False)
    print(f"✓ 成功保存！共 {len(df_normalized)} 行数据")
    
    # 显示结果预览
    print(f"\n结果预览（前5行）:")
    print(df_normalized.head())
    
    # 显示统计信息
    print(f"\n标准化后数据统计:")
    print(df_normalized.describe())
    
    return df_normalized

if __name__ == "__main__":
    import sys
    
    # 测试文件路径
    test_file = "/Users/xiaokong/temp_work/2026/pdq/excel/platform_v2.xlsx"
    
    # 可以从命令行参数获取输入文件
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    
    # 可以从命令行参数获取输出文件
    output_file = None
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    # 可以从命令行参数获取系数
    coefficient = 1.25
    if len(sys.argv) > 3:
        try:
            coefficient = float(sys.argv[3])
        except ValueError:
            print(f"警告: 无效的系数值 '{sys.argv[3]}'，使用默认值 1.25")
    
    try:
        result = normalize_data(test_file, output_file, coefficient)
        print("\n标准化处理完成！")
    except Exception as e:
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()

