/**
 * 折线图
 * 使用ECharts实现，显示多个国家在指定年份范围内的指标变化趋势
 * 
 * 使用方法：
 * const chart = new LineChart({
 *     containerId: 'chart-container',
 *     filename: 'R.json',
 *     topN: 15,
 *     startYear: '2014',
 *     endYear: '2024',
 *     title: '折线图'
 * });
 */

// Tab20颜色映射
const TAB20_COLORS = [
    '#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a',
    '#d62728', '#ff9896', '#9467bd', '#c5b0d5', '#8c564b', '#c49c94',
    '#e377c2', '#f7b6d3', '#7f7f7f', '#c7c7c7', '#bcbd22', '#dbdb8d',
    '#17becf', '#9edae5',
    // 重复以支持更多国家
    '#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a',
    '#d62728', '#ff9896', '#9467bd', '#c5b0d5', '#8c564b', '#c49c94',
    '#e377c2', '#f7b6d3', '#7f7f7f', '#c7c7c7', '#bcbd22', '#dbdb8d',
    '#17becf', '#9edae5'
];

// 分段非线性纵轴：保留0起点，同时放大中高分段，缓解折线粘连
const SCORE_AXIS_STOPS = [
    { raw: 0.0, scaled: 0.0 },
    { raw: 0.4, scaled: 0.08 },
    { raw: 0.55, scaled: 0.48 },
    { raw: 0.7, scaled: 0.72 },
    { raw: 0.85, scaled: 0.9 },
    { raw: 1.0, scaled: 1.0 }
];

function interpolateScoreStops(value, inputKey, outputKey) {
    if (value <= SCORE_AXIS_STOPS[0][inputKey]) {
        return SCORE_AXIS_STOPS[0][outputKey];
    }

    const lastStop = SCORE_AXIS_STOPS[SCORE_AXIS_STOPS.length - 1];
    if (value >= lastStop[inputKey]) {
        return lastStop[outputKey];
    }

    for (let i = 0; i < SCORE_AXIS_STOPS.length - 1; i++) {
        const start = SCORE_AXIS_STOPS[i];
        const end = SCORE_AXIS_STOPS[i + 1];
        if (value >= start[inputKey] && value <= end[inputKey]) {
            const inputRange = end[inputKey] - start[inputKey];
            if (inputRange === 0) {
                return start[outputKey];
            }
            const ratio = (value - start[inputKey]) / inputRange;
            return start[outputKey] + (end[outputKey] - start[outputKey]) * ratio;
        }
    }

    return value;
}

function scaleScoreForDisplay(value) {
    return interpolateScoreStops(value, 'raw', 'scaled');
}

function unscaleScoreForDisplay(value) {
    return interpolateScoreStops(value, 'scaled', 'raw');
}

function formatScoreAxisLabel(value) {
    if (typeof value !== 'number' || Number.isNaN(value)) {
        return value;
    }

    const rawValue = unscaleScoreForDisplay(value);
    return rawValue.toFixed(2);
}

function shouldUseCompressedScoreAxis(values) {
    if (!Array.isArray(values) || values.length === 0) {
        return false;
    }

    const rawMin = Math.min(...values);
    const rawMax = Math.max(...values);
    return rawMin >= 0 && rawMax <= 1.05;
}

/**
 * 折线图类
 */
class LineChart {
    constructor(options = {}) {
        this.containerId = options.containerId || 'chart-container';
        this.filename = options.filename || 'R.json';
        this.topN = options.topN || 15;
        this.startYear = options.startYear || '2014';
        this.endYear = options.endYear || '2024';
        this.title = options.title || '';
        
        this.myChart = null;
        this.currentData = null;
        
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
    }
    
    /**
     * 获取指定年份的top N国家
     */
    async getTopCountries(filename, year, topN) {
        const apiBase = (typeof window !== 'undefined' && window.API_BASE) || '/api';
        const getApiUrl = (typeof window !== 'undefined' && window.getApiUrl) || ((endpoint, params) => {
            const url = new URL(endpoint.startsWith('http') ? endpoint : `${apiBase}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`, window.location.origin);
            const dataSource = (typeof window !== 'undefined' && window.currentDataSource) ? window.currentDataSource() : 'global';
            url.searchParams.set('data_source', dataSource);
            Object.keys(params || {}).forEach(key => url.searchParams.set(key, params[key]));
            return url.toString();
        });
        const url = getApiUrl(`/data/${filename}/top-countries`, { year: year, top_n: topN.toString() });
        
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return data.countries || [];
        } catch (error) {
            console.error('获取top国家失败:', error);
            throw error;
        }
    }
    
    /**
     * 获取国家的时间序列数据
     */
    async getCountryTimeSeries(filename, countries, years) {
        const apiBase = (typeof window !== 'undefined' && window.API_BASE) || '/api';
        const timeSeriesData = {};
        
        const getApiUrl = (typeof window !== 'undefined' && window.getApiUrl) || ((endpoint, params) => {
            const url = new URL(endpoint.startsWith('http') ? endpoint : `${apiBase}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`, window.location.origin);
            const dataSource = (typeof window !== 'undefined' && window.currentDataSource) ? window.currentDataSource() : 'global';
            url.searchParams.set('data_source', dataSource);
            Object.keys(params || {}).forEach(key => url.searchParams.set(key, params[key]));
            return url.toString();
        });
        for (const country of countries) {
            try {
                const response = await fetch(getApiUrl(`/data/${filename}/country/${encodeURIComponent(country)}`));
                if (!response.ok) {
                    console.warn(`获取 ${country} 数据失败`);
                    continue;
                }
                const data = await response.json();
                
                if (data.data && typeof data.data === 'object') {
                    const countryData = {};
                    years.forEach(year => {
                        if (data.data[year] !== undefined) {
                            countryData[year] = data.data[year];
                        }
                    });
                    timeSeriesData[country] = countryData;
                }
            } catch (error) {
                console.warn(`获取 ${country} 数据失败:`, error);
            }
        }
        
        return timeSeriesData;
    }
    
    /**
     * 加载数据并更新图表
     */
    async loadData(filename = null, topN = null, startYear = null, endYear = null, title = null) {
        try {
            // 显示加载状态
            if (this.myChart) {
                this.myChart.showLoading();
            }
            
            const selectedFilename = filename || this.filename;
            const selectedTopN = topN || this.topN;
            const selectedStartYear = startYear || this.startYear;
            const selectedEndYear = endYear || this.endYear;
            const selectedTitle = title || this.title;
            
            // 更新属性
            this.filename = selectedFilename;
            this.topN = selectedTopN;
            this.startYear = selectedStartYear;
            this.endYear = selectedEndYear;
            this.title = selectedTitle;
            
            // 生成年份列表
            const years = [];
            for (let y = parseInt(selectedStartYear); y <= parseInt(selectedEndYear); y++) {
                years.push(String(y));
            }
            
            // 获取指定年份的top N国家（使用结束年份）
            const topCountries = await this.getTopCountries(selectedFilename, selectedEndYear, selectedTopN);
            
            if (topCountries.length === 0) {
                throw new Error('未找到top国家数据');
            }
            
            // 获取这些国家的时间序列数据
            const timeSeriesData = await this.getCountryTimeSeries(selectedFilename, topCountries, years);
            
            // 隐藏加载状态
            if (this.myChart) {
                this.myChart.hideLoading();
            }
            
            // 更新图表
            this.updateChart(timeSeriesData, years, topCountries);
            
            this.currentData = { timeSeriesData, years, topCountries };
            
            return { timeSeriesData, years, topCountries };
        } catch (error) {
            console.error('加载数据失败:', error);
            if (this.myChart) {
                this.myChart.hideLoading();
            }
            throw error;
        }
    }
    
    /**
     * 更新图表
     */
    updateChart(timeSeriesData, years, countries) {
        if (!this.myChart || !timeSeriesData || !years || years.length === 0) {
            return;
        }
        
        const rawSeries = [];
        const allValues = []; // 收集所有有效数值，用于计算动态范围
        
        // 为每个国家创建系列
        countries.forEach((country, countryIdx) => {
            const countryData = timeSeriesData[country] || {};
            const rawValues = years.map(year => {
                const value = countryData[year];
                if (value !== null && value !== undefined && !isNaN(value)) {
                    allValues.push(value);
                    return value;
                }
                return null;
            });

            rawSeries.push({
                name: country,
                color: TAB20_COLORS[countryIdx % TAB20_COLORS.length],
                rawValues
            });
        });

        const useCompressedAxis = shouldUseCompressedScoreAxis(allValues);
        const series = rawSeries.map(({ name, color, rawValues }) => ({
            name: name,
            type: 'line',
            data: rawValues.map(value => {
                if (value === null || value === undefined) {
                    return null;
                }
                return {
                    value: useCompressedAxis ? scaleScoreForDisplay(value) : value,
                    rawValue: value
                };
            }),
            smooth: false,
            symbol: 'circle',
            symbolSize: 5,
            lineStyle: {
                color: color,
                width: 2
            },
            itemStyle: {
                color: color,
                borderColor: 'white',
                borderWidth: 0.8
            },
            label: {
                show: false
            }
        }));
        
        // 计算动态Y轴范围
        let yMin = null;
        let yMax = null;
        if (allValues.length > 0) {
            yMin = 0;
            const rawMax = Math.max(...allValues);
            const rawPadding = Math.max((rawMax - yMin) * 0.05, 0.01);
            const paddedRawMax = useCompressedAxis ? Math.min(1, rawMax + rawPadding) : rawMax + rawPadding;
            yMax = useCompressedAxis ? scaleScoreForDisplay(paddedRawMax) : paddedRawMax;
        }
        
        // 构建option
        const option = {
            title: {
                text: this.title || `${this.filename} - 折线图`,
                left: 'center',
                top: 20,
                textStyle: {
                    fontSize: 16,
                    fontWeight: 'bold'
                }
            },
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'cross'
                },
                formatter: function(params) {
                    let result = params[0].axisValue + '<br/>';
                    params.forEach(function(item) {
                        const value = item.data && typeof item.data === 'object' && item.data.rawValue !== undefined
                            ? item.data.rawValue
                            : item.value;
                        const formattedValue = value !== null && value !== undefined && !isNaN(value) 
                            ? value.toFixed(3) 
                            : 'N/A';
                        result += '<span style="display:inline-block;margin-right:5px;border-radius:50%;width:10px;height:10px;background-color:' 
                            + item.color + ';"></span>' 
                            + item.seriesName + ': ' + formattedValue + '<br/>';
                    });
                    return result;
                }
            },
            legend: {
                data: countries,
                top: 50,
                left: 'center',
                type: 'plain', // 使用plain类型，完整显示所有图例
                orient: 'horizontal',
                textStyle: {
                    fontSize: 12
                },
                itemWidth: 15,
                itemHeight: 10,
                itemGap: 8,
                width: '95%', // 设置图例宽度，确保有足够空间
                selectedMode: false, // 禁用点击切换显示/隐藏功能
                formatter: function(name) {
                    return name; // 完整显示国家名称，不截断
                }
            },
            grid: {
                left: '10%',
                right: '10%',
                top: countries.length > 20 ? '25%' : '20%', // 根据国家数量动态调整top，为图例留出更多空间
                bottom: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: years,
                boundaryGap: false,
                axisLabel: {
                    rotate: 45,
                    fontSize: 10
                },
                axisLine: {
                    show: true
                },
                axisTick: {
                    show: true
                }
            },
            yAxis: {
                type: 'value',
                name: 'Score',
                nameLocation: 'middle',
                nameGap: 50,
                min: yMin !== null ? yMin : undefined,
                max: yMax !== null ? yMax : 1,
                splitNumber: 6,
                axisLabel: {
                    fontSize: 10,
                    formatter: function(value) {
                        if (useCompressedAxis) {
                            return formatScoreAxisLabel(value);
                        }
                        if (typeof value === 'number' && !isNaN(value)) {
                            return value.toFixed(2);
                        }
                        return value;
                    }
                },
                axisPointer: {
                    label: {
                        formatter: function(params) {
                            if (useCompressedAxis) {
                                return formatScoreAxisLabel(params.value);
                            }
                            return typeof params.value === 'number' && !isNaN(params.value)
                                ? params.value.toFixed(2)
                                : params.value;
                        }
                    }
                },
                axisLine: {
                    show: true
                },
                axisTick: {
                    show: true
                },
                splitLine: {
                    show: true,
                    lineStyle: {
                        type: 'dashed',
                        opacity: 0.3
                    }
                }
            },
            series: series
        };
        
        this.myChart.setOption(option, true);
    }
    
    /**
     * 更新配置
     */
    async updateConfig(options) {
        if (options.filename) this.filename = options.filename;
        if (options.topN) this.topN = options.topN;
        if (options.startYear) this.startYear = options.startYear;
        if (options.endYear) this.endYear = options.endYear;
        if (options.title !== undefined) this.title = options.title;
        
        await this.loadData();
    }
    
    /**
     * 销毁图表
     */
    destroy() {
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
    window.LineChart = LineChart;
}
