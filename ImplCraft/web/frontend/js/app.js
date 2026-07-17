/**
 * ImplCraft Frontend Application
 * Metrics analysis, script management, module-level execution tracking
 */

console.log('ImplCraft App loading...');

var API_BASE = '/api';

window.App = {
    currentPage: 'dashboard',
    configData: null,
    flowData: null,
    executionStatus: null,
    statusUpdateInterval: null,
    allDesigns: [],
    currentMetricsDesignId: null,
    metricsTrends: null,
    currentScriptsDesignId: null,
    currentExecDesignId: null,
    allScripts: [],
    previewScriptId: null,

    init: function() {
        console.log('ImplCraft App initializing...');
        try {
            this.setupNavigation();
            this.setupButtons();
            this.loadDashboard();
            this.checkServerStatus();
            this.startStatusPolling();
            this.loadAllDesigns();
            console.log('ImplCraft App initialized successfully');
        } catch (err) {
            console.error('App initialization failed:', err);
        }
    },

    setupNavigation: function() {
        var links = document.querySelectorAll('.nav-menu a');
        var self = this;
        links.forEach(function(link) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                var page = link.dataset.page;
                self.switchPage(page);
            });
        });
    },

    setupButtons: function() {
        document.addEventListener('click', function(e) {
            if (e.target.tagName === 'BUTTON' && e.target.onclick) {
                console.log('Button clicked:', e.target.textContent);
            }
        });
    },

    switchPage: function(page) {
        this.currentPage = page;
        document.querySelectorAll('.page').forEach(function(p) { p.classList.remove('active'); });
        document.querySelectorAll('.nav-menu a').forEach(function(a) { a.classList.remove('active'); });

        var pageEl = document.getElementById('page-' + page);
        var navEl = document.querySelector('[data-page="' + page + '"]');
        if (pageEl) pageEl.classList.add('active');
        if (navEl) navEl.classList.add('active');

        switch (page) {
            case 'dashboard': this.loadDashboard(); break;
            case 'designs': this.loadDesignsList(); break;
            case 'config': this.loadConfig(); break;
            case 'execution': this.initExecutionPage(); break;
            case 'stages': this.loadStages(); break;
            case 'metrics': this.initMetricsPage(); break;
            case 'scripts': this.initScriptsPage(); break;
            case 'risk': this.initRiskPage(); break;
        }
    },

    api: function(path, options) {
        options = options || {};
        var url = API_BASE + path;
        var config = {
            headers: { 'Content-Type': 'application/json' },
            method: options.method || 'GET',
        };
        if (options.body) {
            config.body = typeof options.body === 'object' ? JSON.stringify(options.body) : options.body;
        }
        return fetch(url, config).then(function(response) {
            if (!response.ok) {
                return response.json().catch(function() { return { detail: response.statusText }; }).then(function(err) {
                    throw new Error(err.detail || 'HTTP ' + response.status);
                });
            }
            return response.json();
        });
    },

    async checkServerStatus() {
        try {
            var resp = await fetch('/health');
            var data = await resp.json();
            var dot = document.querySelector('#server-status .status-dot');
            if (dot) dot.className = 'status-dot ' + (data.status === 'healthy' ? 'online' : 'offline');
        } catch (err) {
            var dot2 = document.querySelector('#server-status .status-dot');
            if (dot2) dot2.className = 'status-dot offline';
        }
    },

    startStatusPolling: function() {
        var self = this;
        this.statusUpdateInterval = setInterval(function() {
            if (self.currentPage === 'execution') {
                self.loadExecutionStatus();
                if (self.currentExecDesignId) {
                    self.loadDesignExecStatus(self.currentExecDesignId);
                }
            }
        }, 3000);
    },

    refresh: function() {
        this.switchPage(this.currentPage);
    },

    // ---------- Design list cache ----------
    async loadAllDesigns() {
        try {
            this.allDesigns = await this.api('/designs');
            this.populateDesignSelectors();
        } catch (err) {
            console.error('Load designs failed:', err);
        }
    },

    populateDesignSelectors: function() {
        var selectors = ['metrics-design-select', 'scripts-design-select', 'exec-design-select'];
        var self = this;
        selectors.forEach(function(id) {
            var sel = document.getElementById(id);
            if (!sel) return;
            var currentVal = sel.value;
            sel.innerHTML = '<option value="">选择设计...</option>';
            self.allDesigns.forEach(function(d) {
                var opt = document.createElement('option');
                opt.value = d.id;
                opt.textContent = d.name;
                sel.appendChild(opt);
            });
            if (currentVal) sel.value = currentVal;
        });
    },

    // ==================== DASHBOARD ====================
    async loadDashboard() {
        try {
            var summary = await this.api('/dashboard/summary');
            document.getElementById('stat-designs').textContent = summary.total_designs || 0;
            document.getElementById('stat-active').textContent = summary.active_designs || 0;
            document.getElementById('stat-stages').textContent = summary.total_stages_run || 0;
            document.getElementById('stat-passing').textContent = summary.passing_stages || 0;
            document.getElementById('stat-failing').textContent = summary.failing_stages || 0;
            document.getElementById('stat-scripts').textContent = summary.total_scripts || 0;
            this.loadDesignsOverview();
        } catch (err) {
            console.error('Load dashboard failed:', err);
        }
    },

    async loadDesignsOverview() {
        try {
            var designs = await this.api('/dashboard/designs-overview');
            this.renderDesignsTable(designs);
        } catch (err) {
            console.error('Load designs overview failed:', err);
        }
    },

    renderDesignsTable: function(designs) {
        var tbody = document.getElementById('designs-table-body');
        if (!tbody) return;
        if (!designs || designs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="empty">暂无设计项目</td></tr>';
            return;
        }
        var self = this;
        tbody.innerHTML = designs.map(function(d) {
            var m = d.latest_metrics;
            var wns = m && m.wns != null ? m.wns : '-';
            var tns = m && m.tns != null ? m.tns : '-';
            var drc = m && m.drc_errors != null ? m.drc_errors : '-';
            return '<tr onclick="App.switchPage(\'stages\')" style="cursor:pointer">' +
                '<td><strong>' + self.esc(d.name) + '</strong></td>' +
                '<td><span class="badge badge-' + d.status + '">' + d.status + '</span></td>' +
                '<td>' + self.esc(d.pdk || '-') + '</td>' +
                '<td>' + d.clock_period_ns + '</td>' +
                '<td>' + wns + '</td>' +
                '<td>' + tns + '</td>' +
                '<td>' + drc + '</td>' +
                '<td>' + self.formatDate(d.updated_at) + '</td></tr>';
        }).join('');
    },

    // ==================== DESIGNS ====================
    async loadDesignsList() {
        try {
            var designs = await this.api('/designs');
            var container = document.getElementById('designs-list');
            if (!container) return;
            if (!designs || designs.length === 0) {
                container.innerHTML = '<div class="empty">暂无设计</div>';
                return;
            }
            var self = this;
            container.innerHTML = designs.map(function(d) {
                return '<div class="card">' +
                    '<div class="card-header"><h4>' + self.esc(d.name) + '</h4>' +
                    '<span class="badge badge-' + d.status + '">' + d.status + '</span></div>' +
                    '<div class="card-body">' +
                    '<div class="card-row"><span>顶层模块:</span><span>' + self.esc(d.top_module) + '</span></div>' +
                    '<div class="card-row"><span>PDK:</span><span>' + self.esc(d.pdk_name || '-') + '</span></div>' +
                    '<div class="card-row"><span>时钟周期:</span><span>' + d.clock_period_ns + ' ns</span></div>' +
                    '<div class="card-row"><span>利用率:</span><span>' + (d.target_utilization * 100).toFixed(1) + '%</span></div>' +
                    '<div class="card-row"><span>模块数:</span><span>' + (d.module_count || 0) + '</span></div>' +
                    '</div></div>';
            }).join('');
        } catch (err) {
            console.error('Load designs failed:', err);
        }
    },

    showCreateDesign: function() {
        var modal = document.getElementById('modal-create-design');
        if (modal) modal.classList.remove('hidden');
    },

    async createDesign(event) {
        event.preventDefault();
        var form = event.target;
        var data = {
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
            await this.loadAllDesigns();
            this.loadDesignsList();
            this.loadDashboard();
        } catch (err) {
            alert('创建失败: ' + err.message);
        }
    },

    // ==================== CONFIG ====================
    async loadConfig() {
        try {
            this.configData = await this.api('/config/project');
            this.flowData = await this.api('/config/flow');
            this.renderConfig();
            this.renderFlowConfig();
            this.loadDesignConfigs();
        } catch (err) {
            console.error('Load config failed:', err);
        }
    },

    renderConfig: function() {
        if (!this.configData) return;
        var c = this.configData;
        var nameEl = document.getElementById('config-project-name');
        var dirEl = document.getElementById('config-working-dir');
        if (nameEl) nameEl.value = c.name || '';
        if (dirEl) dirEl.value = c.working_directory || '';
        if (c.eda_tools) {
            var icc2Path = document.getElementById('config-icc2-path');
            var ptPath = document.getElementById('config-pt-path');
            var calibrePath = document.getElementById('config-calibre-path');
            var starrcPath = document.getElementById('config-starrc-path');
            if (icc2Path) icc2Path.value = c.eda_tools.icc2_path || '';
            if (ptPath) ptPath.value = c.eda_tools.pt_path || '';
            if (calibrePath) calibrePath.value = c.eda_tools.calibre_path || '';
            if (starrcPath) starrcPath.value = c.eda_tools.starrc_path || '';
        }
    },

    async loadDesignConfigs() {
        try {
            var designs = await this.api('/config/designs');
            var container = document.getElementById('config-designs-list');
            if (!container) return;
            if (!designs || designs.length === 0) {
                container.innerHTML = '<div class="empty">暂无设计配置</div>';
                return;
            }
            var self = this;
            container.innerHTML = designs.map(function(d) {
                var c = typeof d === 'object' ? d : {};
                var name = c.name || d;
                return '<div class="card" style="margin-bottom:12px">' +
                    '<div class="card-header"><h4>' + self.esc(String(name)) + '</h4>' +
                    '<div><button class="btn btn-sm btn-danger" onclick="App.deleteDesignConfig(\'' + self.esc(String(name)) + '\')">删除</button></div></div>' +
                    '<div class="card-body">' +
                    '<div class="card-row"><span>顶层模块:</span><span>' + self.esc(c.top_module || '-') + '</span></div>' +
                    '<div class="card-row"><span>时钟周期:</span><span>' + (c.clock_period_ns || '-') + ' ns</span></div>' +
                    '<div class="card-row"><span>利用率:</span><span>' + ((c.target_utilization || 0.7) * 100).toFixed(1) + '%</span></div>' +
                    '</div></div>';
            }).join('');
        } catch (err) {
            console.error('Load design configs failed:', err);
        }
    },

    switchConfigTab: function(tab) {
        document.querySelectorAll('.config-panel').forEach(function(p) { p.classList.remove('active'); });
        document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
        var panel = document.getElementById('config-' + tab);
        if (panel) panel.classList.add('active');
        if (event && event.target) event.target.classList.add('active');
    },

    renderFlowConfig: function() {
        if (!this.flowData) return;
        var container = document.getElementById('config-flow-stages');
        if (!container) return;
        var stages = this.flowData.enabled_stages || [];
        var self = this;
        container.innerHTML = stages.map(function(s, i) {
            return '<div class="stage-item">' +
                '<span class="stage-number">' + (i + 1) + '</span>' +
                '<span class="stage-name">' + self.esc(s) + '</span>' +
                '<button class="btn btn-sm" onclick="App.moveStageUp(' + i + ')">↑</button>' +
                '<button class="btn btn-sm" onclick="App.moveStageDown(' + i + ')">↓</button>' +
                '<button class="btn btn-sm btn-danger" onclick="App.removeStage(' + i + ')">×</button></div>';
        }).join('');
    },

    moveStageUp: function(index) {
        if (!this.flowData || index === 0) return;
        var stages = this.flowData.enabled_stages;
        var tmp = stages[index - 1];
        stages[index - 1] = stages[index];
        stages[index] = tmp;
        this.flowData.stage_order = stages.slice();
        this.renderFlowConfig();
    },

    moveStageDown: function(index) {
        if (!this.flowData) return;
        var stages = this.flowData.enabled_stages;
        if (index >= stages.length - 1) return;
        var tmp = stages[index];
        stages[index] = stages[index + 1];
        stages[index + 1] = tmp;
        this.flowData.stage_order = stages.slice();
        this.renderFlowConfig();
    },

    removeStage: function(index) {
        if (!this.flowData) return;
        this.flowData.enabled_stages.splice(index, 1);
        this.flowData.stage_order = this.flowData.enabled_stages.slice();
        this.renderFlowConfig();
    },

    async saveConfig() {
        if (!this.configData) this.configData = {};
        if (!this.flowData) this.flowData = {};
        var pn = document.getElementById('config-project-name');
        var wd = document.getElementById('config-working-dir');
        this.configData.name = pn && pn.value || '';
        this.configData.working_directory = wd && wd.value || '';
        var icc2 = document.getElementById('config-icc2-path');
        var pt = document.getElementById('config-pt-path');
        var cal = document.getElementById('config-calibre-path');
        var star = document.getElementById('config-starrc-path');
        this.configData.eda_tools = {
            icc2_path: icc2 && icc2.value || '',
            pt_path: pt && pt.value || '',
            calibre_path: cal && cal.value || '',
            starrc_path: star && star.value || '',
        };
        var par = document.getElementById('config-parallel');
        var ac = document.getElementById('config-auto-continue');
        var ck = document.getElementById('config-checkpoint');
        this.flowData.parallel_execution = par && par.checked || false;
        this.flowData.auto_continue = ac && ac.checked || false;
        this.flowData.checkpoint_enabled = ck && ck.checked || false;
        try {
            await this.api('/config/project', { method: 'PUT', body: this.configData });
            await this.api('/config/flow', { method: 'PUT', body: this.flowData });
            alert('配置保存成功！');
        } catch (err) {
            alert('保存失败: ' + err.message);
        }
    },

    showCreateDesignConfig: function() {
        var name = prompt('设计配置名称:');
        if (!name) return;
        var topModule = prompt('顶层模块名:');
        if (!topModule) return;
        var clockPeriod = parseFloat(prompt('时钟周期 (ns):', '2.0'));
        var utilization = parseFloat(prompt('目标利用率:', '0.7'));
        var pdk = prompt('PDK 名称:', 'smic28nm');
        var self = this;
        this.api('/config/designs', {
            method: 'POST',
            body: { name: name, top_module: topModule, clock_period_ns: clockPeriod, target_utilization: utilization, pdk_name: pdk }
        }).then(function() {
            self.loadDesignConfigs();
            alert('设计配置创建成功！');
        }).catch(function(err) { alert('创建失败: ' + err.message); });
    },

    async deleteDesignConfig(name) {
        if (!confirm('确定删除配置 "' + name + '"?')) return;
        try {
            await this.api('/config/designs/' + name, { method: 'DELETE' });
            this.loadDesignConfigs();
        } catch (err) {
            alert('删除失败: ' + err.message);
        }
    },

    // ==================== EXECUTION ====================
    async initExecutionPage() {
        await this.loadAllDesigns();
        this.loadExecutionStatus();
        if (this.currentExecDesignId) {
            this.loadDesignExecStatus(this.currentExecDesignId);
        }
    },

    switchExecDesign: function() {
        var sel = document.getElementById('exec-design-select');
        if (!sel) return;
        this.currentExecDesignId = sel.value ? parseInt(sel.value) : null;
        if (this.currentExecDesignId) {
            this.loadDesignExecStatus(this.currentExecDesignId);
            document.getElementById('module-progress-section').style.display = '';
        } else {
            document.getElementById('module-progress-section').style.display = 'none';
        }
    },

    async loadExecutionStatus() {
        try {
            this.executionStatus = await this.api('/execution/status');
            this.renderExecutionStatus();
        } catch (err) {
            console.error('Load execution status failed:', err);
        }
    },

    renderExecutionStatus: function() {
        if (!this.executionStatus) return;
        var status = this.executionStatus.status;
        var statusEl = document.getElementById('exec-status');
        if (statusEl) {
            var dot = statusEl.querySelector('.status-dot');
            var text = statusEl.querySelector('.status-text');
            if (dot) dot.className = 'status-dot ' + status;
            if (text) text.textContent = this.getStatusText(status);
        }
        var startedEl = document.getElementById('exec-started');
        var currentEl = document.getElementById('exec-current');
        if (startedEl) startedEl.textContent = this.executionStatus.started_at ? this.formatDate(this.executionStatus.started_at) : '-';
        if (currentEl) currentEl.textContent = this.executionStatus.current_stage || '-';

        var stages = this.executionStatus.stages || {};
        var flowContainer = document.getElementById('execution-flow');
        if (flowContainer) {
            var self = this;
            flowContainer.innerHTML = Object.keys(stages).map(function(key) {
                var stage = stages[key];
                return '<div class="flow-stage ' + stage.status + '">' +
                    '<div class="flow-stage-header">' +
                    '<span class="flow-stage-name">' + self.esc(stage.name) + '</span>' +
                    '<span class="badge badge-' + stage.status + '">' + self.getStageStatusText(stage.status) + '</span></div>' +
                    '<div class="flow-stage-body">' +
                    '<div class="flow-stage-desc">' + self.esc(stage.description) + '</div>' +
                    '<div class="flow-stage-tool">工具: ' + self.esc(stage.tool) + '</div>' +
                    (stage.duration ? '<div class="flow-stage-time">耗时: ' + stage.duration.toFixed(1) + 's</div>' : '') +
                    '</div></div>';
            }).join('');
        }

        var logs = this.executionStatus.logs || [];
        var logsContainer = document.getElementById('execution-logs');
        if (logsContainer) {
            logsContainer.textContent = logs.join('\n');
            logsContainer.scrollTop = logsContainer.scrollHeight;
        }
    },

    async loadDesignExecStatus(designId) {
        try {
            var data = await this.api('/execution/design-status/' + designId);
            this.renderModuleMatrix(data);
        } catch (err) {
            console.error('Load design exec status failed:', err);
        }
    },

    renderModuleMatrix: function(data) {
        if (!data) return;
        var section = document.getElementById('module-progress-section');
        if (section) section.style.display = '';

        // Summary bar
        var summaryEl = document.getElementById('module-progress-summary');
        if (summaryEl && data.summary) {
            var s = data.summary;
            summaryEl.innerHTML = '<div class="module-summary-stats">' +
                '<span class="summary-item">总模块: <strong>' + s.total_modules + '</strong></span>' +
                '<span class="summary-item summary-running">运行中: <strong>' + s.running + '</strong></span>' +
                '<span class="summary-item summary-completed">已完成: <strong>' + s.completed + '</strong></span>' +
                '<span class="summary-item summary-failed">失败: <strong>' + s.failed + '</strong></span>' +
                '<span class="summary-item summary-pending">等待: <strong>' + s.pending + '</strong></span>' +
                '<span class="summary-item">进度: <strong>' + s.progress_pct + '%</strong></span>' +
                '<div class="progress-bar"><div class="progress-fill" style="width:' + s.progress_pct + '%"></div></div>' +
                '</div>';
        }

        // Matrix table
        var table = document.getElementById('module-matrix-table');
        if (!table) return;
        var stageNames = data.stage_names || [];
        var self = this;

        // Build header
        var headerHtml = '<tr><th>模块</th><th>层级</th>';
        stageNames.forEach(function(sn) {
            headerHtml += '<th>' + self.esc(self.stageLabel(sn)) + '</th>';
        });
        headerHtml += '<th>进度</th></tr>';
        table.querySelector('thead').innerHTML = headerHtml;

        // Build body
        var tbody = table.querySelector('tbody');
        if (!data.modules || data.modules.length === 0) {
            var colspan = stageNames.length + 3;
            tbody.innerHTML = '<tr><td colspan="' + colspan + '" class="empty">暂无模块数据，请在模块划分中添加模块</td></tr>';
            return;
        }

        tbody.innerHTML = data.modules.map(function(m) {
            var completed = 0;
            var row = '<tr>';
            var indent = '';
            for (var li = 0; li < m.level; li++) indent += '  ';
            row += '<td>' + indent + '<strong>' + self.esc(m.name) + '</strong></td>';
            row += '<td>' + self.levelLabel(m.level) + '</td>';

            stageNames.forEach(function(sn) {
                var st = m.stages[sn] || {};
                var status = st.status || 'pending';
                var elapsed = st.elapsed || 0;
                if (status === 'completed' || status === 'skipped') completed++;
                row += '<td><span class="badge badge-' + status + '">' + self.getStageStatusText(status) + '</span>';
                if (elapsed > 0) row += '<br><small style="color:var(--text-muted)">' + elapsed.toFixed(1) + 's</small>';
                row += '</td>';
            });

            var pct = stageNames.length > 0 ? Math.round(completed / stageNames.length * 100) : 0;
            row += '<td><div class="progress-bar" style="width:80px"><div class="progress-fill" style="width:' + pct + '%"></div></div>';
            row += '<small>' + pct + '%</small></td>';
            row += '</tr>';
            return row;
        }).join('');
    },

    refreshModuleProgress: function() {
        if (this.currentExecDesignId) {
            this.loadDesignExecStatus(this.currentExecDesignId);
        }
    },

    async startExecution() {
        try {
            await this.api('/execution/start', { method: 'POST', body: {} });
            this.loadExecutionStatus();
        } catch (err) {
            alert('启动失败: ' + err.message);
        }
    },

    async pauseExecution() {
        try {
            await this.api('/execution/pause', { method: 'POST' });
            this.loadExecutionStatus();
        } catch (err) {
            alert('暂停失败: ' + err.message);
        }
    },

    async resumeExecution() {
        try {
            await this.api('/execution/resume', { method: 'POST' });
            this.loadExecutionStatus();
        } catch (err) {
            alert('继续失败: ' + err.message);
        }
    },

    async stopExecution() {
        try {
            await this.api('/execution/stop', { method: 'POST' });
            this.loadExecutionStatus();
        } catch (err) {
            alert('停止失败: ' + err.message);
        }
    },

    getStatusText: function(status) {
        var map = { idle: '空闲', running: '运行中', paused: '已暂停', completed: '已完成', failed: '失败', stopped: '已停止' };
        return map[status] || status;
    },

    getStageStatusText: function(status) {
        var map = { pending: '等待', running: '运行', completed: '完成', failed: '失败', skipped: '跳过' };
        return map[status] || status;
    },

    stageLabel: function(name) {
        var map = { synthesis: '综合', floorplan: '布局规划', placement: '布局', cts: 'CTS', routing: '布线', drc: 'DRC', lvs: 'LVS', eco_fix: 'ECO' };
        return map[name] || name;
    },

    levelLabel: function(level) {
        var map = { 0: '顶层', 1: '子模块', 2: '子子模块' };
        return map[level] || 'L' + level;
    },

    // ==================== STAGES ====================
    async loadStages() {
        try {
            var stages = await this.api('/stages');
            var container = document.getElementById('stages-list');
            if (!container) return;
            if (!stages || !stages.statuses) {
                container.innerHTML = '<div class="empty">暂无阶段数据</div>';
                return;
            }
            var self = this;
            container.innerHTML = Object.keys(stages.statuses).map(function(key) {
                var stage = stages.statuses[key];
                return '<div class="card">' +
                    '<div class="card-header"><h4>' + self.esc(stage.name) + '</h4>' +
                    '<span class="badge badge-' + stage.status + '">' + self.getStageStatusText(stage.status) + '</span></div>' +
                    '<div class="card-body">' +
                    '<div class="card-row"><span>描述:</span><span>' + self.esc(stage.description) + '</span></div>' +
                    '<div class="card-row"><span>工具:</span><span>' + self.esc(stage.tool) + '</span></div>' +
                    '<div class="card-row"><span>依赖:</span><span>' + (stage.dependencies.join(', ') || '无') + '</span></div>' +
                    (stage.duration ? '<div class="card-row"><span>耗时:</span><span>' + stage.duration.toFixed(1) + 's</span></div>' : '') +
                    '</div></div>';
            }).join('');
        } catch (err) {
            console.error('Load stages failed:', err);
        }
    },

    // ==================== METRICS ====================
    async initMetricsPage() {
        await this.loadAllDesigns();
        if (this.currentMetricsDesignId) {
            this.switchMetricsDesign();
        }
    },

    switchMetricsDesign: function() {
        var sel = document.getElementById('metrics-design-select');
        if (!sel) return;
        this.currentMetricsDesignId = sel.value ? parseInt(sel.value) : null;
        if (this.currentMetricsDesignId) {
            this.loadMetrics();
        } else {
            document.getElementById('metrics-content').innerHTML = '<div class="empty" style="text-align:center;padding:60px 0;color:var(--text-muted)">请选择一个设计以查看指标分析</div>';
            document.getElementById('metrics-tabs').style.display = 'none';
        }
    },

    async loadMetrics() {
        var designId = this.currentMetricsDesignId;
        if (!designId) return;

        try {
            var trends = await this.api('/metrics/' + designId + '/trends');
            this.metricsTrends = trends;

            document.getElementById('metrics-content').style.display = 'none';
            document.getElementById('metrics-tabs').style.display = '';

            this.renderTimingChart(trends);
            this.renderAreaChart(trends);
            this.renderPowerChart(trends);
            this.renderDrcChart(trends);
            this.renderMetricsTable(trends);
        } catch (err) {
            console.error('Load metrics failed:', err);
            document.getElementById('metrics-content').innerHTML = '<div class="empty" style="text-align:center;padding:40px;color:var(--danger)">加载指标数据失败</div>';
        }
    },

    switchMetricsTab: function(tab) {
        var panels = document.querySelectorAll('#metrics-tabs .config-panel');
        panels.forEach(function(p) { p.classList.remove('active'); });
        var btns = document.querySelectorAll('#metrics-tabs .tab-btn');
        btns.forEach(function(b) { b.classList.remove('active'); });
        var panel = document.getElementById('metrics-tab-' + tab);
        if (panel) panel.classList.add('active');
        if (event && event.target) event.target.classList.add('active');
    },

    // ---------- SVG Chart Helpers ----------
    buildLineChart: function(containerId, labels, seriesList, opts) {
        opts = opts || {};
        var W = opts.width || 800;
        var H = opts.height || 300;
        var padL = 65, padR = 120, padT = 30, padB = 40;
        var cW = W - padL - padR;
        var cH = H - padT - padB;

        var allVals = [];
        seriesList.forEach(function(s) {
            s.data.forEach(function(v) { if (v != null) allVals.push(v); });
        });
        if (allVals.length === 0) {
            document.getElementById(containerId).innerHTML = '<div class="empty" style="text-align:center;padding:40px;color:var(--text-muted)">暂无数据</div>';
            return;
        }

        var minV = opts.minY != null ? opts.minY : Math.min.apply(null, allVals);
        var maxV = opts.maxY != null ? opts.maxY : Math.max.apply(null, allVals);
        if (minV === maxV) { minV -= 1; maxV += 1; }
        var range = maxV - minV;
        minV -= range * 0.1;
        maxV += range * 0.1;
        range = maxV - minV;

        function yPos(v) { return padT + cH - ((v - minV) / range * cH); }
        function xPos(i) { return padL + (labels.length > 1 ? i / (labels.length - 1) * cW : cW / 2); }

        var svg = '<svg width="100%" viewBox="0 0 ' + W + ' ' + H + '" style="background:transparent">';

        // Grid lines
        var gridN = 5;
        for (var g = 0; g <= gridN; g++) {
            var y = padT + (g / gridN) * cH;
            var val = maxV - (g / gridN) * range;
            svg += '<line x1="' + padL + '" y1="' + y + '" x2="' + (padL + cW) + '" y2="' + y + '" stroke="#2d3348" stroke-width="1"/>';
            svg += '<text x="' + (padL - 8) + '" y="' + (y + 4) + '" fill="#9ca3af" font-size="11" text-anchor="end">' + val.toFixed(opts.decimals || 1) + '</text>';
        }

        // X labels
        var step = Math.max(1, Math.floor(labels.length / 10));
        for (var i = 0; i < labels.length; i++) {
            if (i % step === 0 || i === labels.length - 1) {
                svg += '<text x="' + xPos(i) + '" y="' + (H - 8) + '" fill="#9ca3af" font-size="11" text-anchor="middle">' + labels[i] + '</text>';
            }
        }

        // Series
        var colors = ['#3b82f6', '#10b981', '#ef4444', '#f59e0b', '#8b5cf6', '#06b6d4'];
        seriesList.forEach(function(s, si) {
            var color = s.color || colors[si % colors.length];
            var pts = [];
            for (var j = 0; j < s.data.length; j++) {
                if (s.data[j] != null) pts.push({ x: xPos(j), y: yPos(s.data[j]), v: s.data[j] });
            }
            if (pts.length > 1) {
                var d = pts.map(function(p, k) { return (k === 0 ? 'M' : 'L') + p.x.toFixed(1) + ' ' + p.y.toFixed(1); }).join(' ');
                svg += '<path d="' + d + '" fill="none" stroke="' + color + '" stroke-width="2"/>';
            }
            pts.forEach(function(p) {
                svg += '<circle cx="' + p.x.toFixed(1) + '" cy="' + p.y.toFixed(1) + '" r="4" fill="' + color + '" stroke="#0f1117" stroke-width="1.5"/>';
            });
        });

        // Legend
        var legendX = W - padR + 15;
        seriesList.forEach(function(s, si) {
            var color = s.color || colors[si % colors.length];
            var ly = padT + si * 22;
            svg += '<rect x="' + legendX + '" y="' + ly + '" width="14" height="14" rx="2" fill="' + color + '"/>';
            svg += '<text x="' + (legendX + 20) + '" y="' + (ly + 11) + '" fill="#e4e6eb" font-size="12">' + s.name + '</text>';
        });

        svg += '</svg>';
        document.getElementById(containerId).innerHTML = svg;
    },

    buildBarChart: function(containerId, labels, seriesList, opts) {
        opts = opts || {};
        var W = opts.width || 800;
        var H = opts.height || 300;
        var padL = 65, padR = 120, padT = 30, padB = 40;
        var cW = W - padL - padR;
        var cH = H - padT - padB;

        var allVals = [];
        seriesList.forEach(function(s) {
            s.data.forEach(function(v) { if (v != null) allVals.push(v); });
        });
        if (allVals.length === 0) {
            document.getElementById(containerId).innerHTML = '<div class="empty" style="text-align:center;padding:40px;color:var(--text-muted)">暂无数据</div>';
            return;
        }

        var minV = 0;
        var maxV = Math.max.apply(null, allVals);
        if (maxV <= 0) maxV = 1;
        maxV *= 1.1;

        function yPos(v) { return padT + cH - (v / maxV * cH); }

        var svg = '<svg width="100%" viewBox="0 0 ' + W + ' ' + H + '" style="background:transparent">';

        // Grid
        for (var g = 0; g <= 5; g++) {
            var y = padT + (g / 5) * cH;
            var val = maxV - (g / 5) * maxV;
            svg += '<line x1="' + padL + '" y1="' + y + '" x2="' + (padL + cW) + '" y2="' + y + '" stroke="#2d3348"/>';
            svg += '<text x="' + (padL - 8) + '" y="' + (y + 4) + '" fill="#9ca3af" font-size="11" text-anchor="end">' + Math.round(val) + '</text>';
        }

        var n = labels.length;
        var nSeries = seriesList.length;
        var groupW = cW / n;
        var barW = Math.min(30, (groupW - 10) / nSeries);
        var colors = ['#3b82f6', '#10b981', '#ef4444', '#f59e0b', '#8b5cf6', '#06b6d4'];

        for (var i = 0; i < n; i++) {
            var cx = padL + i * groupW + groupW / 2;
            svg += '<text x="' + cx + '" y="' + (H - 8) + '" fill="#9ca3af" font-size="11" text-anchor="middle">' + labels[i] + '</text>';

            seriesList.forEach(function(s, si) {
                var v = s.data[i];
                if (v == null) return;
                var bx = cx + (si - nSeries / 2) * (barW + 2);
                var bh = v / maxV * cH;
                var by = padT + cH - bh;
                var color = s.color || colors[si % colors.length];
                svg += '<rect x="' + bx.toFixed(1) + '" y="' + by.toFixed(1) + '" width="' + barW + '" height="' + bh.toFixed(1) + '" rx="2" fill="' + color + '" opacity="0.85"/>';
            });
        }

        // Legend
        var legendX = W - padR + 15;
        seriesList.forEach(function(s, si) {
            var color = s.color || colors[si % colors.length];
            var ly = padT + si * 22;
            svg += '<rect x="' + legendX + '" y="' + ly + '" width="14" height="14" rx="2" fill="' + color + '"/>';
            svg += '<text x="' + (legendX + 20) + '" y="' + (ly + 11) + '" fill="#e4e6eb" font-size="12">' + s.name + '</text>';
        });

        svg += '</svg>';
        document.getElementById(containerId).innerHTML = svg;
    },

    renderTimingChart: function(trends) {
        var labels = trends.iterations.map(function(v) { return '#' + v; });
        this.buildLineChart('chart-timing', labels, [
            { name: 'WNS (ns)', data: trends.wns, color: '#3b82f6' },
            { name: 'TNS (ns)', data: trends.tns, color: '#ef4444' },
        ], { decimals: 2 });
    },

    renderAreaChart: function(trends) {
        var labels = trends.iterations.map(function(v) { return '#' + v; });
        this.buildLineChart('chart-area', labels, [
            { name: '利用率 (%)', data: trends.utilization.map(function(v) { return v != null ? v * 100 : null; }), color: '#10b981' },
        ], { decimals: 1, minY: 0, maxY: 100 });
    },

    renderPowerChart: function(trends) {
        var labels = trends.iterations.map(function(v) { return '#' + v; });
        this.buildLineChart('chart-power', labels, [
            { name: '总功耗 (mW)', data: trends.total_power_mw, color: '#f59e0b' },
            { name: '漏电功耗 (mW)', data: trends.leakage_power_mw, color: '#8b5cf6' },
        ], { decimals: 2 });
    },

    renderDrcChart: function(trends) {
        var labels = trends.iterations.map(function(v) { return '#' + v; });
        this.buildBarChart('chart-drc', labels, [
            { name: 'DRC 错误数', data: trends.drc_errors, color: '#ef4444' },
            { name: '违例路径数', data: trends.num_violating_paths, color: '#f59e0b' },
        ]);
    },

    renderMetricsTable: function(trends) {
        var container = document.getElementById('metrics-table-container');
        if (!container) return;
        var n = trends.iterations.length;
        if (n === 0) {
            container.innerHTML = '<div class="empty">暂无数据</div>';
            return;
        }
        var html = '<table class="data-table"><thead><tr>' +
            '<th>迭代</th><th>时间</th><th>WNS</th><th>TNS</th><th>利用率</th>' +
            '<th>总功耗</th><th>漏电</th><th>DRC</th><th>违例路径</th></tr></thead><tbody>';

        for (var i = n - 1; i >= 0; i--) {
            html += '<tr>' +
                '<td>#' + trends.iterations[i] + '</td>' +
                '<td>' + (trends.timestamps[i] ? this.formatDate(trends.timestamps[i]) : '-') + '</td>' +
                '<td>' + (trends.wns[i] != null ? trends.wns[i].toFixed(3) : '-') + '</td>' +
                '<td>' + (trends.tns[i] != null ? trends.tns[i].toFixed(3) : '-') + '</td>' +
                '<td>' + (trends.utilization[i] != null ? (trends.utilization[i] * 100).toFixed(1) + '%' : '-') + '</td>' +
                '<td>' + (trends.total_power_mw[i] != null ? trends.total_power_mw[i].toFixed(2) + ' mW' : '-') + '</td>' +
                '<td>' + (trends.leakage_power_mw[i] != null ? trends.leakage_power_mw[i].toFixed(2) + ' mW' : '-') + '</td>' +
                '<td>' + (trends.drc_errors[i] != null ? trends.drc_errors[i] : '-') + '</td>' +
                '<td>' + (trends.num_violating_paths[i] != null ? trends.num_violating_paths[i] : '-') + '</td>' +
                '</tr>';
        }
        html += '</tbody></table>';
        container.innerHTML = html;
    },

    // ==================== SCRIPTS ====================
    async initScriptsPage() {
        await this.loadAllDesigns();
        if (this.currentScriptsDesignId) {
            this.loadScripts();
        }
    },

    switchScriptsDesign: function() {
        var sel = document.getElementById('scripts-design-select');
        if (!sel) return;
        this.currentScriptsDesignId = sel.value ? parseInt(sel.value) : null;
        if (this.currentScriptsDesignId) {
            this.loadScripts();
        } else {
            document.getElementById('scripts-table-body').innerHTML = '<tr><td colspan="7" class="empty">请选择设计以查看脚本</td></tr>';
            this.updateScriptStats([]);
        }
    },

    async loadScripts() {
        var designId = this.currentScriptsDesignId;
        if (!designId) return;
        try {
            this.allScripts = await this.api('/scripts/' + designId);
            this.renderScripts(this.allScripts);
            this.updateScriptStats(this.allScripts);
        } catch (err) {
            console.error('Load scripts failed:', err);
        }
    },

    filterScripts: function() {
        var statusFilter = document.getElementById('scripts-filter-status');
        var searchFilter = document.getElementById('scripts-filter-search');
        var status = statusFilter ? statusFilter.value : '';
        var search = searchFilter ? searchFilter.value.toLowerCase() : '';

        var filtered = this.allScripts.filter(function(s) {
            if (status && s.status !== status) return false;
            if (search && s.filename.toLowerCase().indexOf(search) === -1) return false;
            return true;
        });
        this.renderScripts(filtered);
    },

    renderScripts: function(scripts) {
        var tbody = document.getElementById('scripts-table-body');
        if (!tbody) return;
        if (!scripts || scripts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="empty">暂无脚本</td></tr>';
            return;
        }
        var self = this;
        tbody.innerHTML = scripts.map(function(s) {
            return '<tr>' +
                '<td>' + s.id + '</td>' +
                '<td>' + self.esc(s.filename) + '</td>' +
                '<td>' + self.esc(self.stageLabel(s.stage_name)) + '</td>' +
                '<td>' + self.esc(s.script_type) + '</td>' +
                '<td><span class="badge badge-' + s.status + '">' + s.status + '</span></td>' +
                '<td>' + self.formatDate(s.generated_at) + '</td>' +
                '<td>' +
                '<button class="btn btn-sm" onclick="App.previewScript(' + s.id + ')">预览</button> ' +
                (s.status === 'generated' ? '<button class="btn btn-sm btn-primary" onclick="App.executeScript(' + s.id + ')">执行</button> ' : '') +
                (s.status === 'running' ? '<button class="btn btn-sm btn-danger" onclick="App.cancelScript(' + s.id + ')">取消</button> ' : '') +
                (s.execution_log ? '<button class="btn btn-sm" onclick="App.viewScriptLog(' + s.id + ')">日志</button>' : '') +
                '</td></tr>';
        }).join('');
    },

    updateScriptStats: function(scripts) {
        var total = scripts.length;
        var generated = 0, completed = 0, failed = 0;
        scripts.forEach(function(s) {
            if (s.status === 'generated') generated++;
            else if (s.status === 'completed') completed++;
            else if (s.status === 'failed') failed++;
        });
        document.getElementById('script-stat-total').textContent = total;
        document.getElementById('script-stat-generated').textContent = generated;
        document.getElementById('script-stat-completed').textContent = completed;
        document.getElementById('script-stat-failed').textContent = failed;
    },

    showGenerateScript: function() {
        if (!this.currentScriptsDesignId) {
            alert('请先选择一个设计');
            return;
        }
        var modal = document.getElementById('modal-generate-script');
        if (modal) modal.classList.remove('hidden');
    },

    async generateScript(event) {
        event.preventDefault();
        if (!this.currentScriptsDesignId) {
            alert('请先选择一个设计');
            return;
        }
        var form = event.target;
        var data = {
            design_id: this.currentScriptsDesignId,
            stage_name: form.stage_name.value,
            content: form.content.value,
            filename: 'run.tcl',
            script_type: 'tcl',
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
            var script = await this.api('/scripts/preview/' + id);
            this.previewScriptId = id;
            document.getElementById('preview-modal-title').textContent = '脚本预览 — ' + script.filename;
            document.getElementById('preview-meta').textContent = '类型: ' + script.script_type + ' | 行数: ' + script.line_count + ' | 状态: ' + script.status;
            document.getElementById('preview-content').textContent = script.content || '(空)';
            var execBtn = document.getElementById('preview-execute-btn');
            if (execBtn) {
                execBtn.style.display = script.status === 'generated' ? '' : 'none';
            }
            document.getElementById('modal-script-preview').classList.remove('hidden');
        } catch (err) {
            alert('预览失败: ' + err.message);
        }
    },

    async executeFromPreview() {
        if (!this.previewScriptId) return;
        if (!confirm('确定执行此脚本?')) return;
        try {
            await this.api('/scripts/execute', {
                method: 'POST',
                body: { script_id: this.previewScriptId, confirmed: true }
            });
            this.closeModal('modal-script-preview');
            this.loadScripts();
            alert('脚本执行已提交！');
        } catch (err) {
            alert('执行失败: ' + err.message);
        }
    },

    async executeScript(id) {
        if (!confirm('确定执行此脚本?')) return;
        try {
            await this.api('/scripts/execute', {
                method: 'POST',
                body: { script_id: id, confirmed: true }
            });
            this.loadScripts();
            alert('脚本执行已提交！');
        } catch (err) {
            alert('执行失败: ' + err.message);
        }
    },

    async cancelScript(id) {
        if (!confirm('确定取消执行?')) return;
        try {
            await this.api('/scripts/cancel/' + id, { method: 'POST' });
            this.loadScripts();
        } catch (err) {
            alert('取消失败: ' + err.message);
        }
    },

    async viewScriptLog(id) {
        try {
            var log = await this.api('/scripts/log/' + id);
            document.getElementById('log-modal-title').textContent = '执行日志 — ' + log.filename;
            document.getElementById('log-modal-meta').innerHTML =
                '状态: <span class="badge badge-' + log.status + '">' + log.status + '</span>' +
                (log.exit_code != null ? ' | 退出码: ' + log.exit_code : '') +
                (log.executed_at ? ' | 执行时间: ' + this.formatDate(log.executed_at) : '');
            document.getElementById('log-content').textContent = log.execution_log || '(无日志)';
            document.getElementById('modal-script-log').classList.remove('hidden');
        } catch (err) {
            alert('查看日志失败: ' + err.message);
        }
    },

    // ==================== MODULE PARTITION ====================
    showPartitionModal: function() {
        if (!this.currentExecDesignId) {
            alert('请先在执行页面选择设计');
            return;
        }
        document.getElementById('modal-partition').classList.remove('hidden');
    },

    addPartitionRow: function() {
        var container = document.getElementById('partition-modules-list');
        var idx = container.children.length + 1;
        var div = document.createElement('div');
        div.className = 'form-group';
        div.innerHTML = '<label>模块 ' + idx + '</label>' +
            '<div style="display:flex;gap:8px">' +
            '<input type="text" class="form-input partition-module-name" placeholder="模块名称">' +
            '<select class="form-input partition-module-level" style="width:100px">' +
            '<option value="0">顶层</option><option value="1">子模块</option><option value="2">子子模块</option></select>' +
            '<button class="btn btn-sm btn-danger" onclick="this.parentElement.parentElement.parentElement.remove()">删除</button></div>';
        container.appendChild(div);
    },

    async submitPartition() {
        if (!this.currentExecDesignId) return;
        var names = document.querySelectorAll('.partition-module-name');
        var levels = document.querySelectorAll('.partition-module-level');
        var modules = [];
        for (var i = 0; i < names.length; i++) {
            var name = names[i].value.trim();
            if (!name) continue;
            modules.push({
                name: name,
                hierarchy: name,
                level: parseInt(levels[i].value),
            });
        }
        if (modules.length === 0) {
            alert('请至少添加一个模块');
            return;
        }
        try {
            await this.api('/modules/' + this.currentExecDesignId + '/partition', {
                method: 'POST',
                body: { modules: modules }
            });
            this.closeModal('modal-partition');
            this.loadDesignExecStatus(this.currentExecDesignId);
            alert('模块划分保存成功！');
        } catch (err) {
            alert('保存失败: ' + err.message);
        }
    },

    // ==================== RISK ANALYSIS ====================
    riskDesignId: null,
    riskData: null,
    currentDecision: null,

    initRiskPage: function() {
        var sel = document.getElementById('risk-design-select');
        if (sel && sel.options.length <= 1) {
            var self = this;
            this.loadAllDesigns().then(function() {
                self.populateDesignSelectors();
            });
        }
    },

    async loadRiskAnalysis() {
        var sel = document.getElementById('risk-design-select');
        var designId = sel ? sel.value : null;
        if (!designId) return;

        this.riskDesignId = parseInt(designId);
        try {
            this.riskData = await this.api('/risk/analysis/' + designId);
            this.renderRiskOverview();
            this.renderStageRiskCards();
            this.renderDecisionList();
        } catch (err) {
            console.error('Risk analysis failed:', err);
            document.getElementById('risk-meter-label').textContent = '分析失败';
        }
    },

    renderRiskOverview: function() {
        if (!this.riskData) return;
        var risk = this.riskData;

        // Risk meter
        var meter = document.getElementById('risk-meter-fill');
        var label = document.getElementById('risk-meter-label');
        var riskMap = { low: 15, medium: 40, high: 70, critical: 95 };
        var pct = riskMap[risk.overall_risk] || 0;
        meter.style.width = pct + '%';
        label.textContent = this.riskLevelText(risk.overall_risk);

        // Confidence
        var confEl = document.querySelector('#risk-confidence .confidence-value');
        if (confEl) confEl.textContent = Math.round(risk.overall_confidence * 100) + '%';
    },

    renderStageRiskCards: function() {
        var container = document.getElementById('stage-risk-cards');
        if (!container || !this.riskData) return;

        var reports = this.riskData.stage_reports || {};
        var html = '';
        var stages = ['synthesis', 'create_lib', 'floorplan', 'placement', 'cts', 'routing', 'route_opt', 'finish', 'drc', 'lvs'];

        for (var i = 0; i < stages.length; i++) {
            var sn = stages[i];
            var report = reports[sn];
            var riskLevel = report ? report.overall_risk : 'low';
            var risks = report ? (report.risks || []) : [];
            var count = risks.length;

            html += '<div class="stage-risk-card risk-' + riskLevel + '">';
            html += '<h4>' + this.esc(sn);
            if (count > 0) html += ' <span class="risk-count-badge">' + count + ' 风险</span>';
            html += '</h4>';
            html += '<span class="risk-badge ' + riskLevel + '">' + this.riskLevelText(riskLevel) + '</span>';

            if (risks.length > 0) {
                html += '<div class="risk-list" style="margin-top:8px">';
                for (var j = 0; j < Math.min(risks.length, 3); j++) {
                    var r = risks[j];
                    html += '<div class="risk-item risk-' + r.level + '" style="padding:8px 12px;margin-bottom:4px">';
                    html += '<div class="risk-item-body">';
                    html += '<div class="risk-item-title">' + this.esc(r.title) + '</div>';
                    html += '<div class="risk-item-desc">' + this.esc(r.description) + '</div>';
                    html += '<div class="risk-item-meta">';
                    html += '<span class="risk-confidence">' + Math.round(r.confidence * 100) + '% 置信</span>';
                    if (r.decision_required) html += ' <span style="color:#6688ff">需要决策</span>';
                    html += '</div></div>';
                    if (r.decision_required) {
                        html += '<button class="btn btn-sm" onclick="App.showDecisionModal(' + JSON.stringify(r).replace(/'/g, "\'") + ')">决策</button>';
                    }
                    html += '</div>';
                }
                html += '</div>';
            }
            html += '</div>';
        }
        container.innerHTML = html;
    },

    renderDecisionList: function() {
        var container = document.getElementById('risk-decision-list');
        if (!container || !this.riskData) return;

        var decisions = this.riskData.decisions_pending || [];
        if (decisions.length === 0) {
            container.innerHTML = '<p class="empty">暂无待决策项 ✅</p>';
            return;
        }

        var html = '';
        for (var i = 0; i < decisions.length; i++) {
            var d = decisions[i];
            html += '<div class="decision-item">';
            html += '<div class="decision-item-header">';
            html += '<div class="decision-item-title">' + this.esc(d.title) + '</div>';
            html += '<span class="risk-badge ' + d.level + '">' + this.riskLevelText(d.level) + '</span>';
            html += '</div>';
            html += '<div class="decision-item-body">' + this.esc(d.description) + '</div>';
            html += '<div class="decision-item-actions">';
            html += '<button class="btn btn-sm btn-primary" onclick='App.showDecisionModal(' + JSON.stringify(d) + ')'>做出决策</button>';
            html += '</div></div>';
        }
        container.innerHTML = html;
    },

    showDecisionModal: function(risk) {
        this.currentDecision = risk;
        document.getElementById('decision-risk-level').innerHTML =
            '<span class="risk-badge ' + risk.level + '">' + this.riskLevelText(risk.level) + '</span>';
        document.getElementById('decision-title').textContent = risk.title;
        document.getElementById('decision-desc').textContent = risk.description;
        document.getElementById('decision-confidence').textContent =
            '置信度: ' + Math.round(risk.confidence * 100) + '% | 影响阶段: ' + risk.affected_stage;

        var optionsContainer = document.getElementById('decision-options');
        var options = risk.decision_options || [];
        var html = '';
        for (var i = 0; i < options.length; i++) {
            var opt = options[i];
            html += '<div class="decision-option" onclick="App.selectDecision('' + opt.action + '', this)">';
            html += '<div><div class="decision-option-label">' + this.esc(opt.label) + '</div>';
            if (opt.description) html += '<div class="decision-option-desc">' + this.esc(opt.description) + '</div>';
            html += '</div></div>';
        }
        optionsContainer.innerHTML = html;
        document.getElementById('decision-reason').value = '';
        document.getElementById('modal-risk-decision').classList.remove('hidden');
    },

    selectDecision: function(action, el) {
        document.querySelectorAll('.decision-option').forEach(function(o) {
            o.classList.remove('selected');
        });
        el.classList.add('selected');
        this._selectedAction = action;
    },

    async submitDecision() {
        if (!this.currentDecision || !this._selectedAction) {
            alert('请选择一个决策选项');
            return;
        }
        var reason = document.getElementById('decision-reason').value;
        try {
            await this.api('/risk/decision/' + this.riskDesignId, {
                method: 'POST',
                body: {
                    risk_id: this.currentDecision.title,
                    decision: this._selectedAction,
                    reason: reason,
                }
            });
            this.closeModal('modal-risk-decision');
            this.loadRiskAnalysis();
            this._selectedAction = null;
        } catch (err) {
            alert('决策提交失败: ' + err.message);
        }
    },

    async runFullPreflight() {
        if (!this.riskDesignId) {
            alert('请先选择设计');
            return;
        }
        var stages = ['synthesis', 'create_lib', 'floorplan', 'placement', 'cts', 'routing', 'route_opt', 'finish', 'drc', 'lvs'];
        var results = {};
        var allPass = true;

        for (var i = 0; i < stages.length; i++) {
            try {
                var result = await this.api('/risk/preflight/' + this.riskDesignId + '/' + stages[i]);
                results[stages[i]] = result;
                if (!result.effective_pass && result.effective_pass !== undefined) {
                    allPass = false;
                }
            } catch (err) {
                results[stages[i]] = { error: err.message };
                allPass = false;
            }
        }

        var section = document.getElementById('risk-preflight-results');
        section.classList.remove('hidden');

        var html = '<div class="' + (allPass ? 'preflight-pass' : 'preflight-fail') + '">';
        html += allPass ? '✅ 全流程预检通过 — 可以安全执行' : '⚠️ 预检发现问题 — 请查看下方详情并做出决策';
        html += '</div><div style="margin-top:16px">';

        for (var sn in results) {
            var r = results[sn];
            var pass = r.effective_pass !== false;
            html += '<div class="risk-item risk-' + (r.overall_risk || 'low') + '">';
            html += '<div class="risk-item-body">';
            html += '<div class="risk-item-title">' + (pass ? '✅' : '❌') + ' ' + this.esc(sn) + '</div>';
            if (r.blocking_risks && r.blocking_risks.length > 0) {
                for (var j = 0; j < r.blocking_risks.length; j++) {
                    html += '<div class="risk-item-desc">• ' + this.esc(r.blocking_risks[j].title) + '</div>';
                }
            }
            if (r.error) html += '<div class="risk-item-desc" style="color:#ff8800">错误: ' + this.esc(r.error) + '</div>';
            html += '</div></div>';
        }
        html += '</div>';
        document.getElementById('preflight-content').innerHTML = html;
    },

    async loadDashboardRiskSummary(designId) {
        if (!designId) return;
        try {
            var summary = await this.api('/risk/summary/' + designId);
            var counts = summary.risk_counts || {};
            document.querySelector('#risk-critical .risk-count').textContent = counts.critical || 0;
            document.querySelector('#risk-high .risk-count').textContent = counts.high || 0;
            document.querySelector('#risk-medium .risk-count').textContent = counts.medium || 0;
            document.querySelector('#risk-low .risk-count').textContent = counts.low || 0;
            document.querySelector('#risk-decisions .risk-count').textContent = summary.decisions_pending || 0;

            var topList = document.getElementById('risk-top-list');
            if (summary.top_risks && summary.top_risks.length > 0) {
                var html = '';
                for (var i = 0; i < summary.top_risks.length; i++) {
                    var r = summary.top_risks[i];
                    html += '<div class="risk-item risk-' + r.level + '">';
                    html += '<span class="risk-badge ' + r.level + '">' + this.riskLevelText(r.level) + '</span>';
                    html += '<div class="risk-item-body">';
                    html += '<div class="risk-item-title">' + this.esc(r.title) + '</div>';
                    html += '<div class="risk-item-meta">阶段: ' + this.esc(r.stage) + ' | 置信: ' + Math.round(r.confidence * 100) + '%</div>';
                    html += '</div></div>';
                }
                topList.innerHTML = html;
            } else {
                topList.innerHTML = '<p class="empty" style="color:#44bb44">✅ 当前无风险</p>';
            }
        } catch (err) {
            console.error('Dashboard risk summary failed:', err);
        }
    },

    riskLevelText: function(level) {
        var map = { critical: '严重', high: '高', medium: '中', low: '低', unknown: '未知' };
        return map[level] || level;
    },

        // ==================== UTILS ====================
    closeModal: function(modalId) {
        var modal = document.getElementById(modalId);
        if (modal) modal.classList.add('hidden');
    },

    esc: function(str) {
        if (!str) return '';
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },

    formatDate: function(dateStr) {
        if (!dateStr) return '-';
        var d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleString('zh-CN');
    },
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { App.init(); });
} else {
    App.init();
}

console.log('ImplCraft App script loaded');
