/**
 * 动态排序柱状图
 * 显示指定国家在指定时间范围内的R.json数据排名变化
 * 
 * 使用方法：
 * const chart = new DynamicBarChart({
 *     containerId: 'chart-container',
 *     autoPlay: true,
 *     countries: ['United States', 'China', ...],
 *     startYear: '2014',
 *     endYear: '2024'
 * });
 */

// 默认配置
const DEFAULT_COUNTRIES = [
    'United States', 'China', 'United Kingdom', 'Germany', 'France', 'Australia', 'Canada',
    'Spain', 'Switzerland', 'Italy', 'Netherlands (Kingdom of the)',
    'Japan', 'Sweden', 'Finland', 'India', 'Belgium', 'Austria',
    'Denmark', 'Micronesia (Federated States of)', 'Brazil'
];
const DEFAULT_START_YEAR = '2014';
const DEFAULT_END_YEAR = '2024';
const UPDATE_FREQUENCY = 800; // 动画更新频率（毫秒）- 缩短到800ms

// 清新配色方案 - 使用明亮但不刺眼的颜色，确保每个颜色都唯一
// 基于现代设计趋势，使用柔和的渐变色系
const freshColorPalette = [
    '#4A90E2', // 清新蓝
    '#50C878', // 薄荷绿
    '#FF6B9D', // 粉红
    '#FFB347', // 温暖橙
    '#9B59B6', // 淡紫
    '#3498DB', // 天空蓝
    '#1ABC9C', // 青绿
    '#E74C3C', // 珊瑚红
    '#F39C12', // 金黄
    '#16A085', // 翠绿
    '#E67E22', // 橙红
    '#8E44AD', // 紫色
    '#2980B9', // 深蓝
    '#27AE60', // 深绿
    '#C0392B', // 深红
    '#D35400', // 深橙
    '#7F8C8D', // 灰蓝
    '#34495E', // 深灰蓝
    '#1ABC9C', // 青绿（备用）
    '#2ECC71', // 亮绿
    '#3498DB', // 亮蓝
    '#9B59B6', // 亮紫
    '#E91E63', // 玫红
    '#00BCD4', // 青色
    '#FF9800', // 亮橙
    '#795548', // 棕色
    '#607D8B', // 蓝灰
    '#009688', // 青绿
    '#3F51B5', // 靛蓝
    '#FF5722'  // 深橙红
];

// 国家颜色配置（使用清新配色，确保不重复）
const countryColors = {
    'United States': '#4A90E2',        // 清新蓝
    'China': '#E74C3C',      // 珊瑚红
    'United Kingdom': '#3498DB',         // 天空蓝
    'Germany': '#34495E',    // 深灰蓝
    'France': '#9B59B6',     // 淡紫
    'Australia': '#FFB347',  // 温暖橙
    'Canada': '#1ABC9C',     // 青绿
    'Spain': '#FF6B9D',      // 粉红
    'Switzerland': '#50C878', // 薄荷绿
    'Italy': '#F39C12',      // 金黄
    'Netherlands (Kingdom of the)': '#16A085', // 翠绿
    'Japan': '#E67E22',      // 橙红
    'Sweden': '#2980B9',     // 深蓝
    'Finland': '#27AE60',    // 深绿
    'India': '#FF9800',      // 亮橙
    'Belgium': '#8E44AD',    // 紫色
    'Austria': '#C0392B',    // 深红
    'Denmark': '#00BCD4',    // 青色
    'Micronesia (Federated States of)': '#607D8B', // 蓝灰
    'Brazil': '#2ECC71'      // 亮绿
};

// 国家颜色映射（动态生成，确保每个国家都有唯一颜色）
let countryColorMap = {};

/**
 * 为给定的国家列表分配颜色（确保每个国家都有唯一颜色）
 */
function assignColorsToCountries(countries) {
    countryColorMap = {};
    const usedColors = new Set();
    
    // 首先为预定义的国家分配颜色
    countries.forEach((country, index) => {
        // 如果国家在预定义列表中，优先使用预定义颜色（但需要检查是否已被使用）
        if (countryColors[country] && !usedColors.has(countryColors[country])) {
            countryColorMap[country] = countryColors[country];
            usedColors.add(countryColors[country]);
        }
    });
    
    // 然后为剩余的国家从调色板中分配颜色
    countries.forEach((country, index) => {
        // 如果已经分配了颜色，跳过
        if (countryColorMap[country]) {
            return;
        }
        
        // 从清新配色调色板中选择未使用的颜色
        for (let i = 0; i < freshColorPalette.length; i++) {
            const color = freshColorPalette[i];
            if (!usedColors.has(color)) {
                countryColorMap[country] = color;
                usedColors.add(color);
                break;
            }
        }
        
        // 如果调色板用完了，使用HSL生成新颜色（确保与已使用的颜色不同）
        if (!countryColorMap[country]) {
            let hue, saturation, lightness;
            let attempts = 0;
            do {
                // 使用黄金角度确保颜色分布均匀，但调整饱和度和亮度使其更清新
                hue = (index * 137.508 + attempts * 30) % 360;
                saturation = 60 + (attempts % 3) * 10; // 60-80% 饱和度，更柔和
                lightness = 50 + (attempts % 2) * 5;  // 50-55% 亮度，更清新
                attempts++;
            } while (attempts < 100); // 防止无限循环
            
            const generatedColor = `hsl(${hue}, ${saturation}%, ${lightness}%)`;
            countryColorMap[country] = generatedColor;
            usedColors.add(generatedColor);
        }
    });
    
    return countryColorMap;
}

// API基础路径（使用全局变量，如果没有则使用默认值）
// 注意：API_BASE应该在index.html中定义

/**
 * 动态排序柱状图类
 */
class DynamicBarChart {
    constructor(options = {}) {
        this.containerId = options.containerId || 'chart-container';
        this.autoPlay = options.autoPlay !== false; // 默认自动播放
        this.countries = options.countries || DEFAULT_COUNTRIES;
        this.startYear = options.startYear || DEFAULT_START_YEAR;
        this.endYear = options.endYear || DEFAULT_END_YEAR;
        this.filename = options.filename || 'R.json';
        
        this.myChart = null;
        this.currentData = null;
        this.currentYears = [];
        this.animationTimer = null;
        this.currentYearIndex = 0;
        this.allCountries = [];
        
        // 如果提供了countries和filename，则自动初始化
        if (options.countries && options.filename) {
            this.init();
        } else {
            // 否则只初始化图表容器，等待后续调用loadAndPlay
            this.initChart();
        }
    }
    
    /**
     * 初始化
     */
    async init() {
        try {
            // 初始化图表（如果还没初始化）
            if (!this.myChart) {
                this.initChart();
            }
            
            // 加载国家列表
            await this.loadCountries();
            
            // 加载并播放数据
            if (this.autoPlay && this.countries && this.countries.length > 0) {
                await this.loadAndPlay();
            }
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
        
        // 清空容器中的加载提示
        chartDom.innerHTML = '';
        
        this.myChart = echarts.init(chartDom);
        
        // 设置初始配置
        const option = {
            grid: {
                top: 80,
                bottom: 30,
                left: 200,
                right: 100
            },
            xAxis: {
                max: 'dataMax',
                axisLabel: {
                    formatter: function (n) {
                        return n.toFixed(4);
                    }
                }
            },
            yAxis: {
                type: 'category',
                inverse: true,
                max: 20,
                axisLabel: {
                    show: true,
                    fontSize: 14,
                    formatter: function (value) {
                        return value;
                    }
                },
                animationDuration: 300,
                animationDurationUpdate: 300
            },
            series: [
                {
                    realtimeSort: true,
                    seriesLayoutBy: 'column',
                    type: 'bar',
                    itemStyle: {
                        color: (param) => {
                            const country = param.value ? param.value[1] : (param.name || '');
                            // 优先使用动态分配的颜色，如果没有则使用预定义颜色，最后使用默认颜色
                            return countryColorMap[country] || countryColors[country] || '#5470c6';
                        }
                    },
                    label: {
                        show: true,
                        precision: 4,
                        position: 'right',
                        valueAnimation: true,
                        fontFamily: 'monospace',
                        fontSize: 12
                    },
                    encode: {
                        x: 'value',
                        y: 'country'
                    }
                }
            ],
            animationDuration: 0,
            animationDurationUpdate: UPDATE_FREQUENCY,
            animationEasing: 'linear',
            animationEasingUpdate: 'linear',
            graphic: {
                elements: [
                    {
                        type: 'text',
                        right: 160,
                        bottom: 60,
                        style: {
                            text: '',
                            font: 'bolder 80px monospace',
                            fill: 'rgba(100, 100, 100, 0.25)'
                        },
                        z: 100
                    }
                ]
            },
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'shadow'
                },
                formatter: (params) => {
                    const param = params[0];
                    const country = param.value ? param.value[1] : param.name;
                    const value = param.value ? param.value[0] : param.value;
                    const rank = param.dataIndex + 1;
                    return `${country}<br/>Value: ${value.toFixed(4)}<br/>Rank: ${rank}`;
                }
            }
        };
        
        this.myChart.setOption(option);
    }
    
    /**
     * 加载国家列表
     */
    async loadCountries() {
        try {
            const apiBase = (typeof window !== 'undefined' && window.API_BASE) || '/api';
            const getApiUrl = (typeof window !== 'undefined' && window.getApiUrl) || ((endpoint, params) => {
                const url = new URL(endpoint.startsWith('http') ? endpoint : `${apiBase}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`, window.location.origin);
                const dataSource = (typeof window !== 'undefined' && window.currentDataSource) ? window.currentDataSource() : 'global';
                url.searchParams.set('data_source', dataSource);
                Object.keys(params || {}).forEach(key => url.searchParams.set(key, params[key]));
                return url.toString();
            });
            const response = await fetch(getApiUrl(`/data/${this.filename}/countries`));
            const data = await response.json();
            this.allCountries = data.countries || [];
        } catch (error) {
            console.error('加载国家列表失败:', error);
            this.allCountries = [];
        }
    }
    
    /**
     * 从API获取排名数据
     */
    async fetchRankingData(countries, startYear, endYear) {
        const apiBase = (typeof window !== 'undefined' && window.API_BASE) || '/api';
        const getApiUrl = (typeof window !== 'undefined' && window.getApiUrl) || ((endpoint, params) => {
            const url = new URL(endpoint.startsWith('http') ? endpoint : `${apiBase}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`, window.location.origin);
            const dataSource = (typeof window !== 'undefined' && window.currentDataSource) ? window.currentDataSource() : 'global';
            url.searchParams.set('data_source', dataSource);
            Object.keys(params || {}).forEach(key => url.searchParams.set(key, params[key]));
            return url.toString();
        });
        const countriesParam = countries.join(',');
        const url = getApiUrl(`/data/${this.filename}/ranking`, {
            countries: countriesParam,
            start_year: startYear,
            end_year: endYear
        });
        
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('获取排名数据失败:', error);
            throw error;
        }
    }
    
    /**
     * 更新图表数据
     */
    updateChart(yearData, year) {
        if (!this.myChart || !yearData || yearData.length === 0) {
            return;
        }
        
        // 准备数据源
        const source = yearData.map(item => [item.value, item.country]);
        source.unshift(['value', 'country']);
        
        const option = {
            dataset: {
                source: source
            },
            yAxis: {
                max: Math.min(yearData.length - 1, 19)
            },
            graphic: {
                elements: [
                    {
                        type: 'text',
                        right: 160,
                        bottom: 60,
                        style: {
                            text: year,
                            font: 'bolder 80px monospace',
                            fill: 'rgba(100, 100, 100, 0.25)'
                        },
                        z: 100
                    }
                ]
            }
        };
        
        this.myChart.setOption(option);
    }
    
    /**
     * 开始动画播放
     */
    startAnimation(data, years) {
        // 清除之前的定时器
        this.stopAnimation();
        
        this.currentData = data;
        this.currentYears = years;
        this.currentYearIndex = 0;
        
        // 立即显示第一年的数据
        if (this.currentYears.length > 0 && this.currentData[this.currentYears[0]]) {
            this.updateChart(this.currentData[this.currentYears[0]], this.currentYears[0]);
        }
        
        // 开始播放动画（缩短首次延迟）
        const playNext = () => {
            this.currentYearIndex++;
            if (this.currentYearIndex < this.currentYears.length) {
                const year = this.currentYears[this.currentYearIndex];
                if (this.currentData[year]) {
                    this.updateChart(this.currentData[year], year);
                    this.animationTimer = setTimeout(playNext, UPDATE_FREQUENCY);
                }
            }
        };
        
        if (this.currentYears.length > 1) {
            // 缩短首次延迟，让动画更快开始
            this.animationTimer = setTimeout(playNext, UPDATE_FREQUENCY * 0.5); // 首次延迟减半
        }
    }
    
    /**
     * 停止动画
     */
    stopAnimation() {
        if (this.animationTimer) {
            clearTimeout(this.animationTimer);
            this.animationTimer = null;
        }
    }
    
    /**
     * 跳转到指定年份
     */
    jumpToYear(year) {
        if (!this.currentData || !this.currentData[year]) {
            return;
        }
        
        this.stopAnimation();
        this.updateChart(this.currentData[year], year);
        
        const index = this.currentYears.indexOf(year);
        if (index !== -1) {
            this.currentYearIndex = index;
        }
    }
    
    /**
     * 加载并播放数据
     */
    async loadAndPlay(countries = null, startYear = null, endYear = null) {
        try {
            // 显示加载状态
            if (this.myChart) {
                this.myChart.showLoading();
            }
            
            const selectedCountries = countries || this.countries;
            const selectedStartYear = startYear || this.startYear;
            const selectedEndYear = endYear || this.endYear;
            
            // 为当前国家列表分配颜色（确保每个国家都有唯一颜色）
            assignColorsToCountries(selectedCountries);
            
            // 获取数据
            const result = await this.fetchRankingData(selectedCountries, selectedStartYear, selectedEndYear);
            
            // 隐藏加载状态
            if (this.myChart) {
                this.myChart.hideLoading();
            }
            
            // 停止之前的动画
            this.stopAnimation();
            
            // 开始新的动画
            this.startAnimation(result.data, result.years);
            
            return result;
        } catch (error) {
            console.error('加载图表数据失败:', error);
            if (this.myChart) {
                this.myChart.hideLoading();
            }
            throw error;
        }
    }
    
    /**
     * 更新配置并重新加载
     */
    async updateConfig(options) {
        if (options.countries) this.countries = options.countries;
        if (options.startYear) this.startYear = options.startYear;
        if (options.endYear) this.endYear = options.endYear;
        if (options.filename) this.filename = options.filename;
        
        await this.loadAndPlay();
    }
    
    /**
     * 销毁图表
     */
    destroy() {
        this.stopAnimation();
        if (this.myChart) {
            try {
                // 检查DOM元素是否还存在
                const chartDom = document.getElementById(this.containerId);
                if (chartDom) {
                    // DOM元素存在，正常销毁
                    this.myChart.dispose();
                } else {
                    // DOM元素已被移除，只需要清理引用
                    console.warn('图表容器已被移除，跳过dispose');
                }
            } catch (e) {
                // 即使出错也继续清理引用
                console.warn('销毁图表时出错（已忽略）:', e.message);
            } finally {
                // 无论如何都清理引用
                this.myChart = null;
                this.currentData = null;
                this.currentYears = [];
            }
        }
    }
}

// 导出类
if (typeof window !== 'undefined') {
    window.DynamicBarChart = DynamicBarChart;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = DynamicBarChart;
}
