/**
 * 排名变化图
 * 使用Python后端生成图片，前端JS调用并显示
 * 
 * 使用方法：
 * const chart = new RankFlowChart({
 *     containerId: 'chart-container',
 *     filename: 'R.json',
 *     topCountries: ['United States', 'China', 'United Kingdom'],
 *     startYear: '2014',
 *     endYear: '2024',
 *     displayLimit: 26,
 *     title: '排名变化图'
 * });
 */

/**
 * 排名变化图类
 */
class RankFlowChart {
    constructor(options = {}) {
        this.containerId = options.containerId || 'chart-container';
        this.filename = options.filename || 'R.json';
        this.topCountries = options.topCountries || [];
        this.startYear = options.startYear || '2014';
        this.endYear = options.endYear || '2024';
        this.displayLimit = options.displayLimit || 26;
        this.title = options.title || '';
        
        this.imageUrl = null;
        
        this.init();
    }
    
    /**
     * 初始化
     */
    async init() {
        try {
            // 加载数据
            if (this.topCountries.length > 0) {
                await this.loadData();
            }
        } catch (error) {
            console.error('图表初始化失败:', error);
            throw error;
        }
    }
    
    /**
     * 从API获取图片
     */
    async fetchChartImage(filename, countries, startYear, endYear, displayLimit, title) {
        const apiBase = (typeof window !== 'undefined' && window.API_BASE) || '/api';
        const getApiUrl = (typeof window !== 'undefined' && window.getApiUrl) || ((endpoint, params) => {
            const url = new URL(endpoint.startsWith('http') ? endpoint : `${apiBase}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`, window.location.origin);
            const dataSource = (typeof window !== 'undefined' && window.currentDataSource) ? window.currentDataSource() : 'global';
            url.searchParams.set('data_source', dataSource);
            Object.keys(params || {}).forEach(key => url.searchParams.set(key, params[key]));
            return url.toString();
        });
        const countriesStr = countries.join(',');
        const url = getApiUrl(`/chart/rank-flow`, {
            filename: filename,
            countries: countriesStr,
            start_year: startYear,
            end_year: endYear,
            display_limit: displayLimit.toString(),
            title: title
        });
        
        try {
            const response = await fetch(url);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return data.image; // base64编码的图片
        } catch (error) {
            console.error('获取图表图片失败:', error);
            throw error;
        }
    }
    
    /**
     * 加载数据并更新图表
     */
    async loadData(filename = null, topCountries = null, startYear = null, endYear = null, displayLimit = null, title = null) {
        try {
            const chartDom = document.getElementById(this.containerId);
            if (!chartDom) {
                throw new Error(`容器 ${this.containerId} 不存在`);
            }
            
            // 显示加载状态
            chartDom.innerHTML = '<div class="loading">正在生成图表...</div>';
            
            const selectedFilename = filename || this.filename;
            const selectedCountries = topCountries || this.topCountries;
            const selectedStartYear = startYear || this.startYear;
            const selectedEndYear = endYear || this.endYear;
            const selectedDisplayLimit = displayLimit || this.displayLimit;
            const selectedTitle = title || this.title || `${selectedFilename} - 排名变化`;
            
            // 更新属性
            this.filename = selectedFilename;
            this.topCountries = selectedCountries;
            this.startYear = selectedStartYear;
            this.endYear = selectedEndYear;
            this.displayLimit = selectedDisplayLimit;
            this.title = selectedTitle;
            
            // 获取图片
            const imageData = await this.fetchChartImage(
                selectedFilename,
                selectedCountries,
                selectedStartYear,
                selectedEndYear,
                selectedDisplayLimit,
                selectedTitle
            );
            
            this.imageUrl = imageData;
            
            // 显示图片
            chartDom.innerHTML = `<img src="${imageData}" alt="排名变化图" style="max-width: 100%; height: auto;" />`;
            
            return imageData;
        } catch (error) {
            console.error('加载数据失败:', error);
            const chartDom = document.getElementById(this.containerId);
            if (chartDom) {
                chartDom.innerHTML = `<div class="error">加载失败: ${error.message}</div>`;
            }
            throw error;
        }
    }
    
    /**
     * 更新配置
     */
    async updateConfig(options) {
        if (options.filename) this.filename = options.filename;
        if (options.topCountries) this.topCountries = options.topCountries;
        if (options.startYear) this.startYear = options.startYear;
        if (options.endYear) this.endYear = options.endYear;
        if (options.displayLimit) this.displayLimit = options.displayLimit;
        if (options.title !== undefined) this.title = options.title;
        
        await this.loadData();
    }
    
    /**
     * 销毁图表
     */
    destroy() {
        const chartDom = document.getElementById(this.containerId);
        if (chartDom) {
            chartDom.innerHTML = '';
        }
        this.imageUrl = null;
    }
}

// 导出类
if (typeof window !== 'undefined') {
    window.RankFlowChart = RankFlowChart;
}
