/**
 * 大洲柱状图
 * 水平柱状图，按大洲分组显示，支持翻页切换不同大洲
 * 
 * 使用方法：
 * const chart = new ContinentBarChart({
 *     containerId: 'chart-container',
 *     filename: 'R.json',
 *     year: '2024',
 *     name: '开放科学成熟度'
 * });
 */

// 大洲列表（按展示顺序：欧洲、亚洲、北美、南美、非洲、大洋洲）
const DEFAULT_CONTINENTS = ['Europe', 'Asia', 'North America', 'South America', 'Africa', 'Oceania'];

// 大洲中文名称映射
const CONTINENT_NAMES = {
    'Asia': 'Asia',
    'Europe': 'Europe',
    'Africa': 'Africa',
    'North America': 'North America',
    'South America': 'South America',
    'Oceania': 'Oceania',
    'Groups': 'Groups'
};

/**
 * 大洲柱状图类
 */
class ContinentBarChart {
    constructor(options = {}) {
        this.containerId = options.containerId || 'chart-container';
        this.filename = options.filename || 'R.json';
        this.year = options.year || '2024';
        this.name = options.name || null; // 指标名称
        
        this.myChart = null;
        this.currentContinentIndex = 0; // 当前显示的大洲索引
        this.continents = [...DEFAULT_CONTINENTS];
        this.continentData = {}; // 缓存各大洲的数据
        this.currentData = null;
        
        this.init();
    }

    /**
     * 根据当前数据源加载可用分组。全球Plus会额外包含Groups。
     */
    async loadAvailableContinents() {
        const apiBase = (typeof window !== 'undefined' && window.API_BASE) || '/api';
        const getApiUrl = (typeof window !== 'undefined' && window.getApiUrl) || ((endpoint, params) => {
            const url = new URL(endpoint.startsWith('http') ? endpoint : `${apiBase}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`, window.location.origin);
            const dataSource = (typeof window !== 'undefined' && window.currentDataSource) ? window.currentDataSource() : 'global';
            url.searchParams.set('data_source', dataSource);
            Object.keys(params || {}).forEach(key => url.searchParams.set(key, params[key]));
            return url.toString();
        });

        try {
            const response = await fetch(getApiUrl('/continent'));
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const continentMapping = await response.json();
            const extraContinents = Object.keys(continentMapping).filter(continent => !DEFAULT_CONTINENTS.includes(continent));
            this.continents = [
                ...DEFAULT_CONTINENTS.filter(continent => Array.isArray(continentMapping[continent])),
                ...extraContinents
            ];
            if (this.currentContinentIndex >= this.continents.length) {
                this.currentContinentIndex = 0;
            }
        } catch (error) {
            console.warn('加载可用大洲分组失败，使用默认分组:', error);
            this.continents = [...DEFAULT_CONTINENTS];
        }
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
     * 获取大洲数据
     */
    async getContinentData(filename, continent, year) {
        const apiBase = (typeof window !== 'undefined' && window.API_BASE) || '/api';
        const getApiUrl = (typeof window !== 'undefined' && window.getApiUrl) || ((endpoint, params) => {
            const url = new URL(endpoint.startsWith('http') ? endpoint : `${apiBase}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`, window.location.origin);
            const dataSource = (typeof window !== 'undefined' && window.currentDataSource) ? window.currentDataSource() : 'global';
            url.searchParams.set('data_source', dataSource);
            Object.keys(params || {}).forEach(key => url.searchParams.set(key, params[key]));
            return url.toString();
        });
        const url = getApiUrl(`/data/${filename}/continent/${encodeURIComponent(continent)}`);
        
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            
            // 提取指定年份的数据
            if (data.data && data.data[year]) {
                const yearData = data.data[year];
                // 转换为数组并排序（从高到低）
                const countries = Object.keys(yearData)
                    .filter(country => yearData[country] !== null && yearData[country] !== undefined && !isNaN(yearData[country]))
                    .map(country => ({
                        name: country,
                        value: yearData[country]
                    }))
                    .sort((a, b) => b.value - a.value);
                
                return countries;
            }
            return [];
        } catch (error) {
            console.error(`获取大洲 ${continent} 数据失败:`, error);
            return [];
        }
    }
    
    /**
     * 加载所有大洲的数据
     */
    async loadAllContinentsData() {
        // 显示加载状态
        if (this.myChart) {
            this.myChart.showLoading();
        }
        
        try {
            await this.loadAvailableContinents();
            // 并行加载所有大洲的数据
            const promises = this.continents.map(continent =>
                this.getContinentData(this.filename, continent, this.year)
            );
            
            const results = await Promise.all(promises);
            
            // 存储到缓存
            this.continents.forEach((continent, index) => {
                this.continentData[continent] = results[index];
            });
            
            // 隐藏加载状态
            if (this.myChart) {
                this.myChart.hideLoading();
            }
            
            return this.continentData;
        } catch (error) {
            console.error('加载大洲数据失败:', error);
            if (this.myChart) {
                this.myChart.hideLoading();
            }
            throw error;
        }
    }
    
    /**
     * 加载数据并更新图表
     */
    async loadData(filename = null, year = null, name = null) {
        try {
            if (filename) this.filename = filename;
            if (year) this.year = year;
            if (name !== null) this.name = name;
            
            // 加载所有大洲的数据
            await this.loadAllContinentsData();
            
            // 显示当前大洲
            this.updateChart();
            
            return this.continentData;
        } catch (error) {
            console.error('加载数据失败:', error);
            throw error;
        }
    }
    
    /**
     * 更新图表显示
     */
    updateChart() {
        if (!this.myChart) {
            return;
        }
        
        const currentContinent = this.continents[this.currentContinentIndex];
        const continentName = CONTINENT_NAMES[currentContinent] || currentContinent;
        const data = this.continentData[currentContinent] || [];
        
        if (data.length === 0) {
            this.myChart.setOption({
                title: {
                    text: `${continentName} - 暂无数据`,
                    left: 'center',
                    top: 'middle',
                    textStyle: {
                        fontSize: 16,
                        color: '#999'
                    }
                }
            });
            return;
        }
        
        // 准备数据
        const countries = data.map(item => item.name);
        const values = data.map(item => item.value);
        
        // 生成颜色（从深到浅的蓝色渐变）
        const maxValue = Math.max(...values);
        const minValue = Math.min(...values);
        const colorRange = maxValue - minValue;
        
        const colors = values.map(value => {
            const ratio = colorRange > 0 ? (value - minValue) / colorRange : 0.5;
            // 蓝色渐变：从深蓝到浅蓝
            const r = Math.floor(30 + ratio * 100);
            const g = Math.floor(100 + ratio * 100);
            const b = Math.floor(200 - ratio * 50);
            return `rgb(${r}, ${g}, ${b})`;
        });
        
        // 构建option
        const option = {
            title: {
                text: `${continentName} - ${this.name || this.filename}`,
                subtext: `${this.year} | ${data.length} regions`,
                left: 'center',
                top: 20,
                textStyle: {
                    fontSize: 18,
                    fontWeight: 'bold'
                },
                subtextStyle: {
                    fontSize: 12,
                    color: '#666'
                }
            },
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'shadow'
                },
                formatter: function(params) {
                    const param = params[0];
                    const value = param.value;
                    const formattedValue = value !== null && value !== undefined && !isNaN(value) 
                        ? value.toFixed(3) 
                        : 'N/A';
                    return `${param.name}<br/>${param.seriesName}: ${formattedValue}`;
                }
            },
            grid: {
                left: '15%',
                right: '10%',
                top: '15%',
                bottom: '10%',
                containLabel: true
            },
            xAxis: {
                type: 'value',
                name: 'Score',
                nameLocation: 'middle',
                nameGap: 30,
                axisLabel: {
                    formatter: function(value) {
                        return value.toFixed(2);
                    }
                },
                splitLine: {
                    show: true,
                    lineStyle: {
                        type: 'dashed',
                        opacity: 0.3
                    }
                }
            },
            yAxis: {
                type: 'category',
                data: countries,
                axisLabel: {
                    fontSize: 11,
                    interval: 0,
                    formatter: function(value) {
                        // 如果名称太长，截断
                        if (value.length > 15) {
                            return value.substring(0, 15) + '...';
                        }
                        return value;
                    }
                },
                inverse: true // 从高到低显示
            },
            series: [{
                name: 'Score',
                type: 'bar',
                data: values.map((value, index) => ({
                    value: value,
                    itemStyle: {
                        color: colors[index]
                    }
                })),
                label: {
                    show: true,
                    position: 'right',
                    formatter: function(params) {
                        return params.value.toFixed(3);
                    },
                    fontSize: 10
                }
            }]
        };
        
        this.myChart.setOption(option, true);
        this.currentData = { continent: currentContinent, data: data };
    }
    
    /**
     * 切换到下一个大洲
     */
    nextContinent() {
        if (this.currentContinentIndex < this.continents.length - 1) {
            this.currentContinentIndex++;
            this.updateChart();
            return true;
        }
        return false;
    }
    
    /**
     * 切换到上一个大洲
     */
    prevContinent() {
        if (this.currentContinentIndex > 0) {
            this.currentContinentIndex--;
            this.updateChart();
            return true;
        }
        return false;
    }
    
    /**
     * 切换到指定大洲
     */
    goToContinent(index) {
        if (index >= 0 && index < this.continents.length) {
            this.currentContinentIndex = index;
            this.updateChart();
            return true;
        }
        return false;
    }
    
    /**
     * 获取当前大洲信息
     */
    getCurrentContinent() {
        return {
            index: this.currentContinentIndex,
            name: this.continents[this.currentContinentIndex],
            chineseName: CONTINENT_NAMES[this.continents[this.currentContinentIndex]] || this.continents[this.currentContinentIndex],
            total: this.continents.length
        };
    }
    
    /**
     * 更新配置
     */
    async updateConfig(options) {
        if (options.filename) this.filename = options.filename;
        if (options.year) this.year = options.year;
        if (options.name !== undefined) this.name = options.name;
        
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
                this.continentData = {};
            }
        }
    }
}

// 导出类
if (typeof window !== 'undefined') {
    window.ContinentBarChart = ContinentBarChart;
    window.CONTINENTS = DEFAULT_CONTINENTS;
    window.CONTINENT_NAMES = CONTINENT_NAMES;
}
