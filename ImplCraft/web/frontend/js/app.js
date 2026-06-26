/**
 * ImplCraft Frontend Application
 */

console.log('ImplCraft App loading...');

const API_BASE = '/api';

window.App = {
    currentPage: 'dashboard',
    configData: null,
    flowData: null,
    executionStatus: null,
    statusUpdateInterval: null,

    init() {
        console.log('ImplCraft App initializing...');
        try {
            this.setupNavigation();
            this.setupButtons();
            this.loadDashboard();
            this.checkServerStatus();
            this.startStatusPolling();
            console.log('ImplCraft App initialized successfully');
        } catch (err) {
            console.error('App initialization failed:', err);
        }
    },

    setupNavigation() {
        console.log('Setting up navigation...');
        const links = document.querySelectorAll('.nav-menu a');
        console.log(`Found ${links.length} navigation links`);
        
        links.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const page = link.dataset.page;
                console.log(`Navigation clicked: ${page}`);
                this.switchPage(page);
            });
        });
    },

    setupButtons() {
        console.log('Setting up button event handlers...');
        
        // Add event delegation for all buttons with onclick
        document.addEventListener('click', (e) => {
            if (e.target.tagName === 'BUTTON' && e.target.onclick) {
                console.log('Button clicked:', e.target.textContent);
            }
        });
    },

    switchPage(page) {
        console.log(`Switching to page: ${page}`);
        this.currentPage = page;
        
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.querySelectorAll('.nav-menu a').forEach(a => a.classList.remove('active'));

        const pageEl = document.getElementById(`page-${page}`);
        const navEl = document.querySelector(`[data-page="${page}"]`);
        
        if (pageEl) {
            pageEl.classList.add('active');
            console.log(`Page ${page} activated`);
        } else {
            console.error(`Page element not found: page-${page}`);
        }
        
        if (navEl) navEl.classList.add('active');

        switch (page) {
            case 'dashboard': this.loadDashboard(); break;
            case 'designs': this.loadDesignsList(); break;
            case 'config': this.loadConfig(); break;
            case 'execution': this.loadExecutionStatus(); break;
            case 'stages': this.loadStages(); break;
            case 'metrics': this.loadMetrics(); break;
            case 'scripts': this.loadScripts(); break;
        }
    },

    async api(path, options = {}) {
        try {
            const url = `${API_BASE}${path}`;
            console.log(`API call: ${options.method || 'GET'} ${url}`);
            
            const config = {
                headers: { 'Content-Type': 'application/json' },
                ...options,
            };
            
            if (config.body && typeof config.body === 'object') {
                config.body = JSON.stringify(config.body);
            }
            
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            
            return await response.json();
        } catch (err) {
            console.error(`API Error [${path}]:`, err);
            throw err;
        }
    },

    async checkServerStatus() {
        try {
            const resp = await fetch('/health');
            const data = await resp.json();
            const dot = document.querySelector('#server-status .status-dot');
            if (dot) {
                dot.className = `status-dot ${data.status === 'healthy' ? 'online' : 'offline'}`;
            }
        } catch (err) {
            console.error('Server status check failed:', err);
            const dot = document.querySelector('#server-status .status-dot');
            if (dot) dot.className = 'status-dot offline';
        }
    },

    startStatusPolling() {
        this.statusUpdateInterval = setInterval(() => {
            if (this.currentPage === 'execution') {
                this.loadExecutionStatus();
            }
        }, 2000);
    },

    refresh() {
        console.log('Refreshing current page');
        this.switchPage(this.currentPage);
    },

    // Dashboard
    async loadDashboard() {
        try {
            const summary = await this.api('/dashboard/summary');
            document.getElementById('stat-designs').textContent = summary.total_designs || 0;
            document.getElementById('stat-active').textContent = summary.active_designs || 0;
            document.getElementById('stat-stages').textContent = summary.total_stages_run || 0;
            document.getElementById('stat-passing').textContent = summary.passing_stages || 0;
            document.getElementById('stat-failing').textContent = summary.failing_stages || 0;
            document.getElementById('stat-scripts').textContent = summary.total_scripts || 0;

            const designs = await this.api('/designs').catch(() => []);
            this.renderDesignsTable(designs);
        } catch (err) {
            console.error('Dashboard load failed:', err);
        }
    },

    renderDesignsTable(designs) {
        const tbody = document.getElementById('designs-table-body');
        if (!tbody) return;
        
        if (!designs || designs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="empty">暂无设计项目</td></tr>';
            return;
        }
        
        tbody.innerHTML = designs.map(d => `
            <tr onclick="App.switchPage('stages')" style="cursor: pointer;">
                <td><strong>${this.esc(d.name)}</strong></td>
                <td><span class="badge badge-${d.status}">${d.status}</span></td>
                <td>${this.esc(d.pdk_name || '-')}</td>
                <td>${d.clock_period_ns}</td>
                <td>${d.latest_metrics?.wns ?? '-'}</td>
                <td>${d.latest_metrics?.tns ?? '-'}</td>
                <td>${d.latest_metrics?.drc_errors ?? '-'}</td>
                <td>${this.formatDate(d.updated_at)}</td>
            </tr>
        `).join('');
    },

    // Designs
    async loadDesignsList() {
        try {
            const designs = await this.api('/designs');
            const container = document.getElementById('designs-list');
            if (!container) return;
            
            if (!designs || designs.length === 0) {
                container.innerHTML = '<div class="empty">暂无设计项目</div>';
                return;
            }
            
            container.innerHTML = designs.map(d => `
                <div class="card">
                    <div class="card-header">
                        <h4>${this.esc(d.name)}</h4>
                        <span class="badge badge-${d.status}">${d.status}</span>
                    </div>
                    <div class="card-body">
                        <div class="card-row"><span>顶层模块:</span> <span>${this.esc(d.top_module)}</span></div>
                        <div class="card-row"><span>PDK:</span> <span>${this.esc(d.pdk_name || '-')}</span></div>
                        <div class="card-row"><span>时钟周期:</span> <span>${d.clock_period_ns}ns</span></div>
                        <div class="card-row"><span>利用率:</span> <span>${(d.target_utilization * 100).toFixed(1)}%</span></div>
                    </div>
                </div>
            `).join('');
        } catch (err) {
            console.error('Load designs failed:', err);
        }
    },

    showCreateDesign() {
        console.log('Showing create design modal');
        const modal = document.getElementById('modal-create-design');
        if (modal) {
            modal.classList.remove('hidden');
        }
    },

    async createDesign(event) {
        event.preventDefault();
        const form = event.target;
        const data = {
            name: form.name.value,
            top_module: form.top_module.value,
            clock_period_ns: parseFloat(form.clock_period_ns.value),
            target_utilization: parseFloat(form.target_utilization.value),
            pdk_name: form.pdk_name.value,
        };
        
        try {
            await this.api('/designs', { method: 'POST', body: data });
            this.closeModal('modal-create-design');
            form.reset();
            this.loadDesignsList();
            alert('设计创建成功！');
        } catch (err) {
            alert('创建失败: ' + err.message);
        }
    },

    // Config
    async loadConfig() {
        try {
            this.configData = await this.api('/config/project');
            this.flowData = await this.api('/config/flow');
            this.renderConfig();
            this.renderFlowConfig();
            await this.loadDesignConfigs();
        } catch (err) {
            console.error('Load config failed:', err);
        }
    },

    renderConfig() {
        if (!this.configData) return;
        
        document.getElementById('config-project-name').value = this.configData.name || '';
        document.getElementById('config-working-dir').value = this.configData.working_directory || '';
        
        const filesContainer = document.getElementById('config-design-files');
        if (filesContainer) {
            filesContainer.innerHTML = (this.configData.design_files || []).map((f, i) => `
                <div class="file-item">
                    <input type="text" value="${this.esc(f)}" data-index="${i}" onchange="App.updateDesignFile(${i}, this.value)">
                    <button class="btn btn-sm btn-danger" onclick="App.removeDesignFile(${i})">删除</button>
                </div>
            `).join('');
        }

        const libsContainer = document.getElementById('config-design-libs');
        if (libsContainer) {
            libsContainer.innerHTML = (this.configData.design_libraries || []).map((l, i) => `
                <div class="file-item">
                    <input type="text" value="${this.esc(l)}" data-index="${i}" onchange="App.updateDesignLib(${i}, this.value)">
                    <button class="btn btn-sm btn-danger" onclick="App.removeDesignLib(${i})">删除</button>
                </div>
            `).join('');
        }

        const icc2Path = document.getElementById('config-icc2-path');
        const ptPath = document.getElementById('config-pt-path');
        const calibrePath = document.getElementById('config-calibre-path');
        const starrcPath = document.getElementById('config-starrc-path');
        
        if (icc2Path) icc2Path.value = this.configData.eda_tools?.icc2_path || '';
        if (ptPath) ptPath.value = this.configData.eda_tools?.pt_path || '';
        if (calibrePath) calibrePath.value = this.configData.eda_tools?.calibre_path || '';
        if (starrcPath) starrcPath.value = this.configData.eda_tools?.starrc_path || '';
    },

    renderFlowConfig() {
        if (!this.flowData) return;
        
        const stagesContainer = document.getElementById('config-flow-stages');
        if (!stagesContainer) return;
        
        stagesContainer.innerHTML = (this.flowData.enabled_stages || []).map((stage, i) => `
            <div class="stage-item">
                <span class="stage-number">${i + 1}</span>
                <span class="stage-name">${this.esc(stage)}</span>
                <button class="btn btn-sm" onclick="App.moveStageUp(${i})">↑</button>
                <button class="btn btn-sm" onclick="App.moveStageDown(${i})">↓</button>
                <button class="btn btn-sm btn-danger" onclick="App.removeStage(${i})">×</button>
            </div>
        `).join('');

        const parallel = document.getElementById('config-parallel');
        const autoCont = document.getElementById('config-auto-continue');
        const checkpoint = document.getElementById('config-checkpoint');
        
        if (parallel) parallel.checked = this.flowData.parallel_execution || false;
        if (autoCont) autoCont.checked = this.flowData.auto_continue || false;
        if (checkpoint) checkpoint.checked = this.flowData.checkpoint_enabled || false;
    },

    async loadDesignConfigs() {
        try {
            const configs = await this.api('/config/designs');
            const container = document.getElementById('config-designs-list');
            if (!container) return;
            
            if (!configs || configs.length === 0) {
                container.innerHTML = '<div class="empty">暂无设计配置</div>';
                return;
            }
            
            container.innerHTML = configs.map(c => `
                <div class="card">
                    <div class="card-header">
                        <h4>${this.esc(c.name)}</h4>
                        <button class="btn btn-sm btn-danger" onclick="App.deleteDesignConfig('${c.name}')">删除</button>
                    </div>
                    <div class="card-body">
                        <div class="card-row"><span>顶层模块:</span> <span>${this.esc(c.top_module)}</span></div>
                        <div class="card-row"><span>时钟周期:</span> <span>${c.clock_period_ns}ns</span></div>
                        <div class="card-row"><span>利用率:</span> <span>${(c.target_utilization * 100).toFixed(1)}%</span></div>
                    </div>
                </div>
            `).join('');
        } catch (err) {
            console.error('Load design configs failed:', err);
        }
    },

    addDesignFile() {
        console.log('Adding design file');
        if (!this.configData) this.configData = {};
        this.configData.design_files = this.configData.design_files || [];
        this.configData.design_files.push('');
        this.renderConfig();
    },

    updateDesignFile(index, value) {
        if (this.configData) {
            this.configData.design_files[index] = value;
        }
    },

    removeDesignFile(index) {
        if (this.configData && this.configData.design_files) {
            this.configData.design_files.splice(index, 1);
            this.renderConfig();
        }
    },

    addDesignLib() {
        console.log('Adding design lib');
        if (!this.configData) this.configData = {};
        this.configData.design_libraries = this.configData.design_libraries || [];
        this.configData.design_libraries.push('');
        this.renderConfig();
    },

    updateDesignLib(index, value) {
        if (this.configData) {
            this.configData.design_libraries[index] = value;
        }
    },

    removeDesignLib(index) {
        if (this.configData && this.configData.design_libraries) {
            this.configData.design_libraries.splice(index, 1);
            this.renderConfig();
        }
    },

    moveStageUp(index) {
        if (!this.flowData || index === 0) return;
        const stages = this.flowData.enabled_stages;
        [stages[index - 1], stages[index]] = [stages[index], stages[index - 1]];
        this.flowData.stage_order = [...stages];
        this.renderFlowConfig();
    },

    moveStageDown(index) {
        if (!this.flowData) return;
        const stages = this.flowData.enabled_stages;
        if (index >= stages.length - 1) return;
        [stages[index], stages[index + 1]] = [stages[index + 1], stages[index]];
        this.flowData.stage_order = [...stages];
        this.renderFlowConfig();
    },

    removeStage(index) {
        if (!this.flowData) return;
        this.flowData.enabled_stages.splice(index, 1);
        this.flowData.stage_order = [...this.flowData.enabled_stages];
        this.renderFlowConfig();
    },

    switchConfigTab(tab) {
        console.log(`Switching to config tab: ${tab}`);
        document.querySelectorAll('.config-panel').forEach(p => p.classList.remove('active'));
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        
        const panel = document.getElementById(`config-${tab}`);
        if (panel) panel.classList.add('active');
        if (event && event.target) event.target.classList.add('active');
    },

    async saveConfig() {
        console.log('Saving config...');
        
        if (!this.configData) this.configData = {};
        if (!this.flowData) this.flowData = {};
        
        this.configData.name = document.getElementById('config-project-name')?.value || '';
        this.configData.working_directory = document.getElementById('config-working-dir')?.value || '';
        this.configData.eda_tools = {
            icc2_path: document.getElementById('config-icc2-path')?.value || '',
            pt_path: document.getElementById('config-pt-path')?.value || '',
            calibre_path: document.getElementById('config-calibre-path')?.value || '',
            starrc_path: document.getElementById('config-starrc-path')?.value || '',
        };

        this.flowData.parallel_execution = document.getElementById('config-parallel')?.checked || false;
        this.flowData.auto_continue = document.getElementById('config-auto-continue')?.checked || false;
        this.flowData.checkpoint_enabled = document.getElementById('config-checkpoint')?.checked || false;

        try {
            await this.api('/config/project', { method: 'PUT', body: this.configData });
            await this.api('/config/flow', { method: 'PUT', body: this.flowData });
            alert('配置保存成功！');
        } catch (err) {
            alert('保存失败: ' + err.message);
        }
    },

    showCreateDesignConfig() {
        const name = prompt('设计配置名称:');
        if (!name) return;
        const topModule = prompt('顶层模块名:');
        if (!topModule) return;
        const clockPeriod = parseFloat(prompt('时钟周期 (ns):', '2.0'));
        const utilization = parseFloat(prompt('目标利用率:', '0.7'));
        const pdk = prompt('PDK 名称:', 'smic28nm');

        this.api('/config/designs', {
            method: 'POST',
            body: {
                name, top_module: topModule,
                clock_period_ns: clockPeriod,
                target_utilization: utilization,
                pdk_name: pdk
            }
        }).then(() => {
            this.loadDesignConfigs();
            alert('设计配置创建成功！');
        }).catch(err => alert('创建失败: ' + err.message));
    },

    async deleteDesignConfig(name) {
        if (!confirm(`确定删除配置 "${name}"?`)) return;
        try {
            await this.api(`/config/designs/${name}`, { method: 'DELETE' });
            this.loadDesignConfigs();
        } catch (err) {
            alert('删除失败: ' + err.message);
        }
    },

    // Execution
    async loadExecutionStatus() {
        try {
            this.executionStatus = await this.api('/execution/status');
            this.renderExecutionStatus();
        } catch (err) {
            console.error('Load execution status failed:', err);
        }
    },

    renderExecutionStatus() {
        if (!this.executionStatus) return;

        const status = this.executionStatus.status;
        const statusEl = document.getElementById('exec-status');
        if (statusEl) {
            const dot = statusEl.querySelector('.status-dot');
            const text = statusEl.querySelector('.status-text');
            if (dot) dot.className = `status-dot ${status}`;
            if (text) text.textContent = this.getStatusText(status);
        }

        const startedEl = document.getElementById('exec-started');
        const currentEl = document.getElementById('exec-current');
        
        if (startedEl) {
            startedEl.textContent = this.executionStatus.started_at ? this.formatDate(this.executionStatus.started_at) : '-';
        }
        if (currentEl) {
            currentEl.textContent = this.executionStatus.current_stage || '-';
        }

        const stages = this.executionStatus.stages || {};
        const flowContainer = document.getElementById('execution-flow');
        if (flowContainer) {
            flowContainer.innerHTML = Object.entries(stages).map(([key, stage]) => `
                <div class="flow-stage ${stage.status}">
                    <div class="flow-stage-header">
                        <span class="flow-stage-name">${this.esc(stage.name)}</span>
                        <span class="badge badge-${stage.status}">${this.getStageStatusText(stage.status)}</span>
                    </div>
                    <div class="flow-stage-body">
                        <div class="flow-stage-desc">${this.esc(stage.description)}</div>
                        <div class="flow-stage-tool">工具: ${this.esc(stage.tool)}</div>
                        ${stage.duration ? `<div class="flow-stage-time">耗时: ${stage.duration.toFixed(1)}s</div>` : ''}
                    </div>
                </div>
            `).join('');
        }

        const logs = this.executionStatus.logs || [];
        const logsContainer = document.getElementById('execution-logs');
        if (logsContainer) {
            logsContainer.textContent = logs.join('\n');
            logsContainer.scrollTop = logsContainer.scrollHeight;
        }
    },

    getStatusText(status) {
        const map = { idle: '空闲', running: '运行中', paused: '已暂停', completed: '已完成', failed: '失败', stopped: '已停止' };
        return map[status] || status;
    },

    getStageStatusText(status) {
        const map = { pending: '等待', running: '运行', completed: '完成', failed: '失败', skipped: '跳过' };
        return map[status] || status;
    },

    async startExecution() {
        console.log('Starting execution...');
        try {
            const flowConfig = await this.api('/config/flow');
            await this.api('/execution/start', {
                method: 'POST',
                body: { stage_order: flowConfig.enabled_stages }
            });
            this.loadExecutionStatus();
            alert('执行流程已启动！');
        } catch (err) {
            alert('启动失败: ' + err.message);
        }
    },

    async pauseExecution() {
        console.log('Pausing execution...');
        try {
            await this.api('/execution/pause', { method: 'POST' });
            this.loadExecutionStatus();
        } catch (err) {
            alert('暂停失败: ' + err.message);
        }
    },

    async resumeExecution() {
        console.log('Resuming execution...');
        try {
            await this.api('/execution/resume', { method: 'POST' });
            this.loadExecutionStatus();
        } catch (err) {
            alert('继续失败: ' + err.message);
        }
    },

    async stopExecution() {
        console.log('Stopping execution...');
        if (!confirm('确定停止执行?')) return;
        try {
            await this.api('/execution/stop', { method: 'POST' });
            this.loadExecutionStatus();
        } catch (err) {
            alert('停止失败: ' + err.message);
        }
    },

    // Stages
    async loadStages() {
        try {
            const stages = await this.api('/execution/stages');
            const container = document.getElementById('stages-list');
            if (!container) return;
            
            container.innerHTML = Object.entries(stages.statuses).map(([key, stage]) => `
                <div class="card">
                    <div class="card-header">
                        <h4>${this.esc(stage.name)}</h4>
                        <span class="badge badge-${stage.status}">${this.getStageStatusText(stage.status)}</span>
                    </div>
                    <div class="card-body">
                        <div class="card-row"><span>描述:</span> <span>${this.esc(stage.description)}</span></div>
                        <div class="card-row"><span>工具:</span> <span>${this.esc(stage.tool)}</span></div>
                        <div class="card-row"><span>依赖:</span> <span>${stage.dependencies.join(', ') || '无'}</span></div>
                        ${stage.duration ? `<div class="card-row"><span>耗时:</span> <span>${stage.duration.toFixed(1)}s</span></div>` : ''}
                    </div>
                </div>
            `).join('');
        } catch (err) {
            console.error('Load stages failed:', err);
        }
    },

    // Metrics
    async loadMetrics() {
        const container = document.getElementById('metrics-content');
        if (container) {
            container.innerHTML = '<div class="empty">指标分析功能开发中...</div>';
        }
    },

    // Scripts
    async loadScripts() {
        try {
            const scripts = await this.api('/scripts');
            const tbody = document.getElementById('scripts-table-body');
            if (!tbody) return;
            
            if (!scripts || scripts.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="empty">暂无脚本</td></tr>';
                return;
            }
            
            tbody.innerHTML = scripts.map(s => `
                <tr>
                    <td>${s.id}</td>
                    <td>${this.esc(s.filename)}</td>
                    <td>${this.esc(s.script_type)}</td>
                    <td><span class="badge badge-${s.status}">${s.status}</span></td>
                    <td>${this.formatDate(s.generated_at)}</td>
                    <td>
                        <button class="btn btn-sm" onclick="App.previewScript(${s.id})">预览</button>
                        <button class="btn btn-sm btn-primary" onclick="App.executeScript(${s.id})">执行</button>
                    </td>
                </tr>
            `).join('');
        } catch (err) {
            console.error('Load scripts failed:', err);
        }
    },

    showGenerateScript() {
        console.log('Showing generate script modal');
        const modal = document.getElementById('modal-generate-script');
        if (modal) {
            modal.classList.remove('hidden');
        }
    },

    async generateScript(event) {
        event.preventDefault();
        const form = event.target;
        const data = {
            design_id: 1,
            stage_name: form.stage_name.value,
            content: form.content.value,
            filename: 'run.tcl',
            script_type: 'tcl'
        };
        
        try {
            await this.api('/scripts/generate', { method: 'POST', body: data });
            this.closeModal('modal-generate-script');
            form.reset();
            this.loadScripts();
            alert('脚本生成成功！');
        } catch (err) {
            alert('生成失败: ' + err.message);
        }
    },

    async previewScript(id) {
        try {
            const script = await this.api(`/scripts/preview/${id}`);
            alert(`脚本预览:\n\n${script.content.substring(0, 500)}...`);
        } catch (err) {
            alert('预览失败: ' + err.message);
        }
    },

    async executeScript(id) {
        if (!confirm('确定执行此脚本?')) return;
        try {
            await this.api('/scripts/execute', {
                method: 'POST',
                body: { script_id: id, confirmed: true }
            });
            alert('脚本执行已提交！');
        } catch (err) {
            alert('执行失败: ' + err.message);
        }
    },

    // Utils
    closeModal(modalId) {
        console.log(`Closing modal: ${modalId}`);
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('hidden');
        }
    },

    esc(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },

    formatDate(dateStr) {
        if (!dateStr) return '-';
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleString('zh-CN');
    },
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => App.init());
} else {
    App.init();
}

console.log('ImplCraft App script loaded');
