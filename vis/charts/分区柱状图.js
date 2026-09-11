/**
 * 分区柱状图
 * 按分位数将数据分成6个层级，使用2x3子图布局显示
 * 
 * 使用方法：
 * const chart = new TierBarChart({
 *     containerId: 'chart-container',
 *     filename: 'R.json',
 *     year: '2024'
 * });
 */

// 自定义分位数
const CUSTOM_QUANTILES = [0, 0.25, 0.50, 0.70, 0.85, 0.95, 1.0];
const TIER_LABELS = [0, 1, 2, 3, 4, 5]; // Tier 0-5
const PLOT_TIERS = [5, 4, 3, 2, 1, 0]; // 从高到低显示

/**
 * 分区柱状图类
 */
class TierBarChart {
    constructor(options = {}) {
        this.containerId = options.containerId || 'chart-container';
        this.filename = options.filename || 'R.json';
        this.year = options.year || '2024';
        this.name = options.name || null; // 指标名称，从name.json获取
        
        this.myChart = null;
        this.currentData = null;
        this.resizeHandler = null; // 窗口resize处理器
        
        this.init();
    }
    
    /**
     * 初始化
     */
    async init() {
        try {
            // 初始化图表
            this.initChart();
            
            // 加载数据
            await this.loadData();
        } catch (error) {
            console.error('图表初始化失败:', error);
            throw error;
        }
    }
    
    /**
     * 初始化图表
     */
    initChart() {
        const chartDom = document.getElementById(this.containerId);
        if (!chartDom) {
            throw new Error(`容器 ${this.containerId} 不存在`);
        }
        
        // 清空容器
        chartDom.innerHTML = '';
        
        this.myChart = echarts.init(chartDom);
        
        // 添加窗口resize监听器，确保图表能响应窗口大小变化
        this.resizeHandler = () => {
            if (this.myChart) {
                this.myChart.resize();
            }
        };
        window.addEventListener('resize', this.resizeHandler);
    }
    
    /**
     * 从API获取数据
     */
    async fetchData(filename, year) {
        const apiBase = (typeof window !== 'undefined' && window.API_BASE) || '/api';
        const getApiUrl = (typeof window !== 'undefined' && window.getApiUrl) || ((endpoint, params) => {
            const url = new URL(endpoint.startsWith('http') ? endpoint : `${apiBase}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`, window.location.origin);
            const dataSource = (typeof window !== 'undefined' && window.currentDataSource) ? window.currentDataSource() : 'global';
            url.searchParams.set('data_source', dataSource);
            Object.keys(params || {}).forEach(key => url.searchParams.set(key, params[key]));
            return url.toString();
        });
        const url = getApiUrl(`/data/${filename}/year/${year}`);
        
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log('分区柱状图获取的数据:', data);
            return data;
        } catch (error) {
            console.error('获取数据失败:', error);
            throw error;
        }
    }
    
    /**
     * 计算分位数（类似pandas qcut）
     */
    calculateQuantiles(scores) {
        if (scores.length === 0) return [];
        
        const sortedScores = [...scores].sort((a, b) => a - b);
        const quantiles = [];
        
        for (let q of CUSTOM_QUANTILES) {
            if (q === 0) {
                quantiles.push(sortedScores[0]);
            } else if (q === 1) {
                quantiles.push(sortedScores[sortedScores.length - 1]);
            } else {
                const index = q * (sortedScores.length - 1);
                const lower = Math.floor(index);
                const upper = Math.ceil(index);
                const weight = index - lower;
                
                if (lower === upper) {
                    quantiles.push(sortedScores[lower]);
                } else {
                    quantiles.push(sortedScores[lower] * (1 - weight) + sortedScores[upper] * weight);
                }
            }
        }
        
        return quantiles;
    }
    
    /**
     * 将国家分配到Tier（类似pandas qcut）
     * 使用分位数切割，确保每个区间有大致相同数量的数据点
     */
    assignTiers(countryScores) {
        // 提取所有分数并创建国家-分数对
        const entries = Object.entries(countryScores)
            .filter(([country, score]) => score != null && !isNaN(score))
            .map(([country, score]) => ({ country, score }));
        
        if (entries.length === 0) {
            return { tieredData: {}, quantiles: [], tierCounts: {} };
        }
        
        // 按分数降序排序（最高分在前）
        entries.sort((a, b) => b.score - a.score);
        
        const total = entries.length;
        
        // 计算每个分位数对应的索引位置（类似pandas qcut）
        // custom_quantiles = [0, 0.25, 0.50, 0.70, 0.85, 0.95, 1.0]
        // 这意味着：
        // Tier 5: 0% - 5% (最高分，索引0到5%)
        // Tier 4: 5% - 15% (索引5%到15%)
        // Tier 3: 15% - 30% (索引15%到30%)
        // Tier 2: 30% - 50% (索引30%到50%)
        // Tier 1: 50% - 75% (索引50%到75%)
        // Tier 0: 75% - 100% (索引75%到100%，最低分)
        
        // 计算分位数值（用于显示）
        const quantiles = CUSTOM_QUANTILES.map(q => {
            if (q === 0) return entries[total - 1].score; // 最低分
            if (q === 1) return entries[0].score; // 最高分
            const idx = Math.floor(q * (total - 1));
            return entries[idx].score;
        });
        
        // 计算每个Tier的索引范围（类似pandas qcut）
        // custom_quantiles = [0, 0.25, 0.50, 0.70, 0.85, 0.95, 1.0]
        // entries是按分数降序排序的（最高分在前，idx=0）
        // qcut会将数据分成6个区间，从低到高标记为Tier 0-5
        // 但由于entries是降序，我们需要反转：
        // Tier 5 (最高5%): idx 0 到 idx (0.05 * total - 1) - 对应quantiles[5]到quantiles[6] (0.95到1.0)
        // Tier 4 (5%-15%): idx (0.05 * total) 到 idx (0.15 * total - 1) - 对应quantiles[4]到quantiles[5] (0.85到0.95)
        // Tier 3 (15%-30%): idx (0.15 * total) 到 idx (0.30 * total - 1) - 对应quantiles[3]到quantiles[4] (0.70到0.85)
        // Tier 2 (30%-50%): idx (0.30 * total) 到 idx (0.50 * total - 1) - 对应quantiles[2]到quantiles[3] (0.50到0.70)
        // Tier 1 (50%-75%): idx (0.50 * total) 到 idx (0.75 * total - 1) - 对应quantiles[1]到quantiles[2] (0.25到0.50)
        // Tier 0 (75%-100%,最低): idx (0.75 * total) 到 idx (total-1) - 对应quantiles[0]到quantiles[1] (0到0.25)
        
        const tierRanges = [];
        for (let i = 0; i < CUSTOM_QUANTILES.length - 1; i++) {
            const startQ = CUSTOM_QUANTILES[i];
            const endQ = CUSTOM_QUANTILES[i + 1];
            // 由于entries是降序，需要反转分位数
            // quantiles[5]-quantiles[6] (0.95-1.0) 对应最高分，应该是idx 0到5%
            const startIdx = Math.floor((1 - endQ) * total);
            const endIdx = Math.floor((1 - startQ) * total) - 1;
            // i=0对应Tier 0, i=5对应Tier 5
            tierRanges.push({ startIdx: Math.max(0, startIdx), endIdx: Math.min(total - 1, endIdx), tier: i });
        }
        
        // 分配Tier（基于索引位置，类似qcut）
        const tieredData = {};
        const tierCounts = {};
        
        for (let i = 0; i < TIER_LABELS.length; i++) {
            tierCounts[i] = 0;
            tieredData[i] = [];
        }
        
        // 按索引位置分配（从高到低）
        entries.forEach((entry, idx) => {
            // 找到这个索引属于哪个Tier
            let assignedTier = 0; // 默认最低Tier
            for (let i = 0; i < tierRanges.length; i++) {
                const range = tierRanges[i];
                if (idx >= range.startIdx && idx <= range.endIdx) {
                    assignedTier = range.tier;
                    break;
                }
            }
            
            tieredData[assignedTier].push(entry);
            tierCounts[assignedTier] = (tierCounts[assignedTier] || 0) + 1;
        });
        
        // 对每个Tier内的数据按分数排序（降序，从高到低显示）
        Object.keys(tieredData).forEach(tier => {
            tieredData[tier].sort((a, b) => b.score - a.score);
        });
        
        console.log('Tier分配详情:', {
            total,
            tierCounts,
            tierRanges: tierRanges.map(r => ({ tier: r.tier, range: `${r.startIdx}-${r.endIdx}` }))
        });
        
        return { tieredData, quantiles, tierCounts };
    }
    
    /**
     * 生成颜色（从深到浅的蓝色系，Tier 5最深，Tier 0最浅）
     */
    generateTierColor(tier) {
        // 6个Tier，从深蓝到浅蓝
        // Tier 5 (最高分) - 最深蓝色
        // Tier 0 (最低分) - 最浅蓝色
        const colors = {
            5: '#003f7f', // 最深蓝
            4: '#0052a3',
            3: '#0066cc',
            2: '#4d94ff',
            1: '#80b3ff',
            0: '#b3d9ff'  // 最浅蓝
        };
        return colors[tier] || '#5470c6';
    }
    
    /**
     * 更新图表
     */
    updateChart(countryScores, year) {
        if (!this.myChart || !countryScores) {
            console.warn('图表未初始化或数据为空');
            return;
        }
        
        console.log('更新分区柱状图，国家数量:', Object.keys(countryScores).length);
        
        // 分配Tier
        const { tieredData, quantiles, tierCounts } = this.assignTiers(countryScores);
        
        console.log('Tier分配结果:', {
            tierCounts,
            totalCountries: Object.values(tierCounts).reduce((a, b) => a + b, 0)
        });
        
        // 创建2x3网格布局（2行3列）
        const grids = [];
        const series = [];
        const xAxes = [];
        const yAxes = [];
        
        // 使用百分比布局，确保总高度和总宽度不超过100%
        // 纵向计算：topMargin + gridHeightPercent + rowGapPercent + gridHeightPercent <= 100%
        // 横向计算：leftMargin + gridWidthPercent + gapPercent + gridWidthPercent + gapPercent + gridWidthPercent + rightMargin <= 100%
        const topMargin = 12; // 顶部边距（为主标题留空间）
        const gridHeightPercent = 40; // 每行高度40%（两行共80%，加上间距和边距约95%）
        const rowGapPercent = 3; // 行间距3%
        
        const leftMargin = 10; // 左边距（为Y轴标签预留空间）
        const gridWidthPercent = 28; // 每列宽度28%（三列共84%，加上间距约96%）
        const gapPercent = 2; // 列间距2%
        const rightMargin = 2; // 右边距
        
        // 生成6个grid（2行3列）
        for (let idx = 0; idx < PLOT_TIERS.length; idx++) {
            const tier = PLOT_TIERS[idx];
            const row = Math.floor(idx / 3);
            const col = idx % 3;
            
            // 计算每个grid的位置
            const left = leftMargin + col * (gridWidthPercent + gapPercent);
            const top = topMargin + row * (gridHeightPercent + rowGapPercent);
            
            grids.push({
                left: `${left}%`,
                top: `${top}%`,
                width: `${gridWidthPercent}%`,
                height: `${gridHeightPercent}%`,
                containLabel: true, // 重新启用，让ECharts自动处理Y轴标签空间，但我们已经预留了足够的leftMargin
                right: `${rightMargin}%`, // 右边距
                bottom: '5%' // 底部边距
            });
            
            // 准备该Tier的数据
            const tierData = tieredData[tier] || [];
            const count = tierData.length;
            
            // 如果没有数据，创建空的series（但仍然显示）
            if (count === 0) {
                xAxes.push({
                    gridIndex: idx,
                    type: 'value',
                    name: 'Score',
                    nameLocation: 'middle',
                    nameGap: 25,
                    axisLabel: {
                        fontSize: 9
                    }
                });
                
                yAxes.push({
                    gridIndex: idx,
                    type: 'category',
                    data: ['No Data'],
                    inverse: true,
                    axisLabel: {
                        fontSize: 11
                    }
                });
                
                series.push({
                    type: 'bar',
                    xAxisIndex: idx,
                    yAxisIndex: idx,
                    data: [0],
                    itemStyle: {
                        color: '#e0e0e0'
                    },
                    label: {
                        show: false
                    },
                    silent: true
                });
                continue;
            }
            
            const countries = tierData.map(d => d.country);
            const scores = tierData.map(d => d.score);
            
            // 计算百分比范围
            // custom_quantiles = [0, 0.25, 0.50, 0.70, 0.85, 0.95, 1.0]
            // Tier 5对应quantiles[5]-quantiles[6] (0.95-1.0)，即Top 5%-0%
            // Tier 4对应quantiles[4]-quantiles[5] (0.85-0.95)，即Top 15%-5%
            // Tier 3对应quantiles[3]-quantiles[4] (0.70-0.85)，即Top 30%-15%
            // Tier 2对应quantiles[2]-quantiles[3] (0.50-0.70)，即Top 50%-30%
            // Tier 1对应quantiles[1]-quantiles[2] (0.25-0.50)，即Top 75%-50%
            // Tier 0对应quantiles[0]-quantiles[1] (0-0.25)，即Top 100%-75%
            const quantileIdx = tier; // tier直接对应quantiles的起始索引
            const percentStart = (1 - CUSTOM_QUANTILES[quantileIdx + 1]) * 100;
            const percentEnd = (1 - CUSTOM_QUANTILES[quantileIdx]) * 100;
            
            // X轴（数值轴）
            xAxes.push({
                gridIndex: idx,
                type: 'value',
                name: 'Score',
                nameLocation: 'middle',
                nameGap: 25,
                axisLabel: {
                    fontSize: 9
                }
            });
            
            // Y轴（类别轴）
            yAxes.push({
                gridIndex: idx,
                type: 'category',
                data: countries,
                inverse: true, // 从高到低显示（最高分在顶部）
                axisLabel: {
                    fontSize: count > 40 ? 8 : (count > 20 ? 9 : 11),
                    width: 70, // 固定像素宽度，配合containLabel使用
                    overflow: 'truncate', // 截断过长的标签
                    ellipsis: '...', // 超出部分显示省略号
                    interval: 0 // 显示所有标签
                },
                axisLine: {
                    show: true
                },
                axisTick: {
                    show: true
                }
            });
            
            // 系列数据
            series.push({
                type: 'bar',
                xAxisIndex: idx,
                yAxisIndex: idx,
                data: scores,
                itemStyle: {
                    color: this.generateTierColor(tier),
                    borderColor: '#666',
                    borderWidth: 1
                },
                label: {
                    show: true,
                    position: 'right',
                    formatter: (params) => {
                        return params.value.toFixed(3);
                    },
                    fontSize: count > 40 ? 5 : (count > 20 ? 7 : 9)
                },
                barWidth: '60%'
            });
        }
        
        // 为每个grid创建title
        const titles = PLOT_TIERS.map((tier, idx) => {
            const tierData = tieredData[tier] || [];
            const count = tierData.length;
            // 计算百分比范围
            // tier 5对应quantiles[5]-quantiles[6] (0.95-1.0)，即Top 5%-0%
            // tier 4对应quantiles[4]-quantiles[5] (0.85-0.95)，即Top 15%-5%
            // tier 3对应quantiles[3]-quantiles[4] (0.70-0.85)，即Top 30%-15%
            // tier 2对应quantiles[2]-quantiles[3] (0.50-0.70)，即Top 50%-30%
            // tier 1对应quantiles[1]-quantiles[2] (0.25-0.50)，即Top 75%-50%
            // tier 0对应quantiles[0]-quantiles[1] (0-0.25)，即Top 100%-75%
            const quantileIdx = tier; // tier直接对应quantiles的起始索引
            const percentStart = (1 - CUSTOM_QUANTILES[quantileIdx + 1]) * 100;
            const percentEnd = (1 - CUSTOM_QUANTILES[quantileIdx]) * 100;
            
            const row = Math.floor(idx / 3);
            const col = idx % 3;
            const left = leftMargin + col * (gridWidthPercent + gapPercent);
            const top = topMargin + row * (gridHeightPercent + rowGapPercent);
            
            const titleText = count === 0 
                ? `Tier ${tier} (Top ${percentStart.toFixed(0)}% - ${percentEnd.toFixed(0)}%) | No Data`
                : `Tier ${tier} (Top ${percentStart.toFixed(0)}% - ${percentEnd.toFixed(0)}%) | Count: ${count}`;
            
            return {
                text: titleText,
                left: `${left + gridWidthPercent / 2}%`,
                top: `${top - 2}%`, // 调整位置，避免与子图重合但不要太远
                textAlign: 'center',
                textStyle: {
                    fontSize: 11,
                    fontWeight: 'bold',
                    color: '#333'
                },
                backgroundColor: '#f0f0f0',
                padding: [3, 6],
                borderRadius: 3
            };
        });
        
        // 添加主标题（使用name.json中的映射名称）
        const displayName = this.name || this.filename;
        titles.unshift({
            text: `${displayName} - ${year}`,
            left: 'center',
            top: 10,
            textStyle: {
                fontSize: 16,
                fontWeight: 'bold'
            }
        });
        
        // 构建option
        const option = {
            title: titles,
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'shadow'
                },
                confine: true, // 确保tooltip始终在图表容器内，不会超出页面边缘
                formatter: (params) => {
                    const param = params[0];
                    return `${param.name}<br/>Score: ${param.value.toFixed(4)}`;
                }
            },
            grid: grids,
            xAxis: xAxes,
            yAxis: yAxes,
            series: series
        };
        
        console.log('设置图表选项，grids数量:', grids.length, 'series数量:', series.length);
        console.log('Grids配置:', grids);
        
        try {
            this.myChart.setOption(option, true); // 使用notMerge完全替换
            this.currentData = { countryScores, year, tieredData };
            console.log('分区柱状图更新成功');
        } catch (error) {
            console.error('设置图表选项失败:', error);
            throw error;
        }
    }
    
    /**
     * 加载数据
     */
    async loadData(filename = null, year = null) {
        try {
            // 显示加载状态
            if (this.myChart) {
                this.myChart.showLoading();
            }
            
            const selectedFilename = filename || this.filename;
            const selectedYear = year || this.year;
            
            // 更新属性
            this.filename = selectedFilename;
            this.year = selectedYear;
            
            // 获取数据
            const result = await this.fetchData(selectedFilename, selectedYear);
            
            // 隐藏加载状态
            if (this.myChart) {
                this.myChart.hideLoading();
            }
            
            // 更新图表
            console.log('分区柱状图数据结果:', result);
            if (result.data && typeof result.data === 'object') {
                console.log('更新图表，数据量:', Object.keys(result.data).length);
                this.updateChart(result.data, selectedYear);
            } else {
                console.error('数据格式不正确:', result);
                throw new Error('数据格式不正确，期望对象类型');
            }
            
            return result;
        } catch (error) {
            console.error('加载数据失败:', error);
            if (this.myChart) {
                this.myChart.hideLoading();
            }
            throw error;
        }
    }
    
    /**
     * 更新配置
     */
    async updateConfig(options) {
        if (options.filename) this.filename = options.filename;
        if (options.year) this.year = options.year;
        
        await this.loadData();
    }
    
    /**
     * 销毁图表
     */
    destroy() {
        // 移除resize监听器
        if (this.resizeHandler) {
            window.removeEventListener('resize', this.resizeHandler);
            this.resizeHandler = null;
        }
        
        if (this.myChart) {
            try {
                const chartDom = document.getElementById(this.containerId);
                if (chartDom) {
                    this.myChart.dispose();
                } else {
                    console.warn('图表容器已被移除，跳过dispose');
                }
            } catch (e) {
                console.warn('销毁图表时出错（已忽略）:', e.message);
            } finally {
                this.myChart = null;
                this.currentData = null;
            }
        }
    }
}

// 导出类
if (typeof window !== 'undefined') {
    window.TierBarChart = TierBarChart;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = TierBarChart;
}

