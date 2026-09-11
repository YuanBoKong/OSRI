/**
 * 对比折线图
 * 支持自由选择多个国家进行对比，可选择时间范围和指标
 * 
 * 使用方法：
 * const chart = new CompareLineChart({
 *     containerId: 'chart-container',
 *     filename: 'R.json',
 *     countries: ['China', 'United States'],
 *     startYear: '2014',
 *     endYear: '2024',
 *     name: '开放科学准备度'
 * });
 */

// Tab20颜色映射（扩展版，支持更多国家）
const COMPARE_TAB20_COLORS = [
    '#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a',
    '#d62728', '#ff9896', '#9467bd', '#c5b0d5', '#8c564b', '#c49c94',
    '#e377c2', '#f7b6d3', '#7f7f7f', '#c7c7c7', '#bcbd22', '#dbdb8d',
    '#17becf', '#9edae5',
    // 重复以支持更多国家
    '#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a',
    '#d62728', '#ff9896', '#9467bd', '#c5b0d5', '#8c564b', '#c49c94',
    '#e377c2', '#f7b6d3', '#7f7f7f', '#c7c7c7', '#bcbd22', '#dbdb8d',
    '#17becf', '#9edae5',
    // 第三轮
    '#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a',
    '#d62728', '#ff9896', '#9467bd', '#c5b0d5', '#8c564b', '#c49c94',
    '#e377c2', '#f7b6d3', '#7f7f7f', '#c7c7c7', '#bcbd22', '#dbdb8d',
    '#17becf', '#9edae5'
];

// 分段非线性纵轴：保留0起点，同时放大中高分段，缓解折线粘连
const COMPARE_SCORE_AXIS_STOPS = [
    { raw: 0.0, scaled: 0.0 },
    { raw: 0.4, scaled: 0.08 },
    { raw: 0.55, scaled: 0.48 },
    { raw: 0.7, scaled: 0.72 },
    { raw: 0.85, scaled: 0.9 },
    { raw: 1.0, scaled: 1.0 }
];

function interpolateCompareScoreStops(value, inputKey, outputKey) {
    if (value <= COMPARE_SCORE_AXIS_STOPS[0][inputKey]) {
        return COMPARE_SCORE_AXIS_STOPS[0][outputKey];
    }

    const lastStop = COMPARE_SCORE_AXIS_STOPS[COMPARE_SCORE_AXIS_STOPS.length - 1];
    if (value >= lastStop[inputKey]) {
        return lastStop[outputKey];
    }

    for (let i = 0; i < COMPARE_SCORE_AXIS_STOPS.length - 1; i++) {
        const start = COMPARE_SCORE_AXIS_STOPS[i];
        const end = COMPARE_SCORE_AXIS_STOPS[i + 1];
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

function scaleCompareScoreForDisplay(value) {
    return interpolateCompareScoreStops(value, 'raw', 'scaled');
}

function unscaleCompareScoreForDisplay(value) {
    return interpolateCompareScoreStops(value, 'scaled', 'raw');
}

function formatCompareScoreAxisLabel(value) {
    if (typeof value !== 'number' || Number.isNaN(value)) {
        return value;
    }

    return unscaleCompareScoreForDisplay(value).toFixed(2);
}

function shouldUseCompressedCompareScoreAxis(values) {
    if (!Array.isArray(values) || values.length === 0) {
        return false;
    }

    const rawMin = Math.min(...values);
    const rawMax = Math.max(...values);
    return rawMin >= 0 && rawMax <= 1.05;
}

/**
 * 对比折线图类
 */
class CompareLineChart {
    constructor(options = {}) {
        this.containerId = options.containerId || 'chart-container';
        this.filename = options.filename || 'R.json';
        this.countries = options.countries || [];
        this.startYear = options.startYear || '2014';
        this.endYear = options.endYear || '2024';
        this.name = options.name || null;
        
        this.myChart = null;
        this.currentData = null;
        this.allCountries = []; // 所有可用国家列表
        this.continentData = {}; // 大洲数据
        
        this.init();
    }
    
    /**
     * 初始化
     */
    async init() {
        try {
            // 加载所有国家列表
            await this.loadAllCountries();
            
            // 初始化图表
            this.initChart();
            
            // 加载数据
            if (this.countries.length > 0) {
                await this.loadData();
            }
        } catch (error) {
            console.error('图表初始化失败:', error);
            throw error;
        }
    }
    
    /**
     * 加载所有国家列表和大洲数据（从continent.json）
     */
    async loadAllCountries() {
        const apiBase = (typeof window !== 'undefined' && window.API_BASE) || '/api';
        const getApiUrl = (typeof window !== 'undefined' && window.getApiUrl) || ((endpoint, params) => {
            const url = new URL(endpoint.startsWith('http') ? endpoint : `${apiBase}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`, window.location.origin);
            const dataSource = (typeof window !== 'undefined' && window.currentDataSource) ? window.currentDataSource() : 'global';
            url.searchParams.set('data_source', dataSource);
            Object.keys(params || {}).forEach(key => url.searchParams.set(key, params[key]));
            return url.toString();
        });
        const url = getApiUrl(`/continent`);
        
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            
            // 保存大洲数据
            this.continentData = data;
            
            // 合并所有大洲的国家
            const allCountriesSet = new Set();
            for (const continent in data) {
                if (Array.isArray(data[continent])) {
                    data[continent].forEach(country => allCountriesSet.add(country));
                }
            }
            
            this.allCountries = Array.from(allCountriesSet).sort();
            return this.allCountries;
        } catch (error) {
            console.error('加载国家列表失败:', error);
            throw error;
        }
    }
    
    /**
     * 获取大洲数据
     */
    getContinentData() {
        return this.continentData || {};
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
        // 并行获取所有国家的数据
        const promises = countries.map(async (country) => {
            try {
                const response = await fetch(getApiUrl(`/data/${filename}/country/${encodeURIComponent(country)}`));
                if (!response.ok) {
                    console.warn(`获取 ${country} 数据失败`);
                    return { country, data: null };
                }
                const data = await response.json();
                
                if (data.data && typeof data.data === 'object') {
                    const countryData = {};
                    years.forEach(year => {
                        if (data.data[year] !== undefined) {
                            countryData[year] = data.data[year];
                        }
                    });
                    return { country, data: countryData };
                }
                return { country, data: null };
            } catch (error) {
                console.warn(`获取 ${country} 数据失败:`, error);
                return { country, data: null };
            }
        });
        
        const results = await Promise.all(promises);
        results.forEach(({ country, data }) => {
            if (data) {
                timeSeriesData[country] = data;
            }
        });
        
        return timeSeriesData;
    }
    
    /**
     * 加载数据并更新图表
     */
    async loadData(filename = null, countries = null, startYear = null, endYear = null, name = null) {
        try {
            // 显示加载状态
            if (this.myChart) {
                this.myChart.showLoading();
            }
            
            const selectedFilename = filename || this.filename;
            const selectedCountries = countries || this.countries;
            const selectedStartYear = startYear || this.startYear;
            const selectedEndYear = endYear || this.endYear;
            const selectedName = name !== null ? name : this.name;
            
            // 更新属性
            this.filename = selectedFilename;
            this.countries = selectedCountries;
            this.startYear = selectedStartYear;
            this.endYear = selectedEndYear;
            this.name = selectedName;
            
            if (selectedCountries.length === 0) {
                if (this.myChart) {
                    this.myChart.hideLoading();
                }
                this.showEmptyChart();
                return;
            }
            
            // 生成年份列表
            const years = [];
            for (let y = parseInt(selectedStartYear); y <= parseInt(selectedEndYear); y++) {
                years.push(String(y));
            }
            
            // 获取这些国家的时间序列数据
            const timeSeriesData = await this.getCountryTimeSeries(selectedFilename, selectedCountries, years);
            
            // 隐藏加载状态
            if (this.myChart) {
                this.myChart.hideLoading();
            }
            
            // 更新图表
            this.updateChart(timeSeriesData, years, selectedCountries);
            
            this.currentData = { timeSeriesData, years, countries: selectedCountries };
            
            return { timeSeriesData, years, countries: selectedCountries };
        } catch (error) {
            console.error('加载数据失败:', error);
            if (this.myChart) {
                this.myChart.hideLoading();
            }
            throw error;
        }
    }
    
    /**
     * 显示空图表
     */
    showEmptyChart() {
        if (!this.myChart) {
            return;
        }
        
        const option = {
            title: {
                text: '请选择至少一个国家进行对比',
                left: 'center',
                top: 'middle',
                textStyle: {
                    fontSize: 16,
                    color: '#999'
                }
            }
        };
        
        this.myChart.setOption(option, true);
    }
    
    /**
     * 更新图表
     */
    updateChart(timeSeriesData, years, countries) {
        if (!this.myChart || !timeSeriesData || !years || years.length === 0 || countries.length === 0) {
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
                color: COMPARE_TAB20_COLORS[countryIdx % COMPARE_TAB20_COLORS.length],
                rawValues
            });
        });

        const useCompressedAxis = shouldUseCompressedCompareScoreAxis(allValues);
        const series = rawSeries.map(({ name, color, rawValues }) => ({
            name: name,
            type: 'line',
            data: rawValues.map(value => {
                if (value === null || value === undefined) {
                    return null;
                }
                return {
                    value: useCompressedAxis ? scaleCompareScoreForDisplay(value) : value,
                    rawValue: value
                };
            }),
            smooth: true,
            symbol: 'circle',
            symbolSize: 6,
            lineStyle: {
                color: color,
                width: 2.5
            },
            itemStyle: {
                color: color,
                borderColor: 'white',
                borderWidth: 1.5
            },
            label: {
                show: false
            },
            emphasis: {
                focus: 'series',
                lineStyle: {
                    width: 3.5
                }
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
            yMax = useCompressedAxis ? scaleCompareScoreForDisplay(paddedRawMax) : paddedRawMax;
        }
        
        // 构建option
        const option = {
            title: {
                text: this.name || `${this.filename} - 对比折线图`,
                left: 'center',
                top: 20,
                textStyle: {
                    fontSize: 18,
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
                type: 'plain',
                orient: 'horizontal',
                textStyle: {
                    fontSize: 12
                },
                itemWidth: 15,
                itemHeight: 10,
                itemGap: 10
            },
            grid: {
                left: '10%',
                right: '10%',
                top: '20%',
                bottom: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: years,
                boundaryGap: false,
                axisLabel: {
                    rotate: 45,
                    fontSize: 11,
                    color: '#666'
                },
                axisLine: {
                    show: true,
                    lineStyle: {
                        color: '#ccc'
                    }
                },
                axisTick: {
                    show: true,
                    lineStyle: {
                        color: '#ccc'
                    }
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
                nameTextStyle: {
                    color: '#666'
                },
                axisLabel: {
                    fontSize: 11,
                    color: '#666',
                    formatter: function(value) {
                        if (useCompressedAxis) {
                            return formatCompareScoreAxisLabel(value);
                        }
                        return typeof value === 'number' && !isNaN(value)
                            ? value.toFixed(2)
                            : value;
                    }
                },
                axisPointer: {
                    label: {
                        formatter: function(params) {
                            if (useCompressedAxis) {
                                return formatCompareScoreAxisLabel(params.value);
                            }
                            return typeof params.value === 'number' && !isNaN(params.value)
                                ? params.value.toFixed(2)
                                : params.value;
                        }
                    }
                },
                axisLine: {
                    show: true,
                    lineStyle: {
                        color: '#ccc'
                    }
                },
                axisTick: {
                    show: true,
                    lineStyle: {
                        color: '#ccc'
                    }
                },
                splitLine: {
                    show: true,
                    lineStyle: {
                        type: 'dashed',
                        color: '#e0e0e0',
                        opacity: 0.5
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
        if (options.countries) this.countries = options.countries;
        if (options.startYear) this.startYear = options.startYear;
        if (options.endYear) this.endYear = options.endYear;
        if (options.name !== undefined) this.name = options.name;
        
        await this.loadData();
    }
    
    /**
     * 获取所有可用国家列表
     */
    getAllCountries() {
        return this.allCountries;
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
    window.CompareLineChart = CompareLineChart;
}
