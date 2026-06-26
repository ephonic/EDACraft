/**
 * ImplCraft Frontend Application
 * Professional design management dashboard with real-time updates.
 */

const API_BASE = '/api';

const App = {
    currentPage: 'dashboard',
    charts: {},
    currentScriptId: null,

    // ─── Initialization ─────────────────────────────────────────

    init() {
        this.setupNavigation();
        this.loadDashboard();
        this.checkServerStatus();
        this.connectWebSocket();
    },

    setupNavigation() {
        document.querySelectorAll('.nav-menu a').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.dataset.page;
                this.switchPage(page);
            });
        });
    },

    switchPage(page) {
        this.currentPage = page;
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.querySelectorAll('.nav-menu a').forEach(a => a.classList.remove('active'));

        const pageEl = document.getElementById(`page-${page}`);
        const navEl = document.querySelector(`[data-page="${page}"]`);
        if (pageEl) pageEl.classList.add('active');
        if (navEl) navEl.classList.add('active');

        switch (page) {
            case 'dashboard': this.loadDashboard(); break;
            case 'designs': this.loadDesignsList(); break;
            case 'stages': this.populateDesignSelect('stage-design-select'); break;
            case 'metrics': this.populateDesignSelect('metrics-design-select'); break;
            case 'scripts': this.populateDesignSelect('scripts-design-select'); break;
            case 'git': this.loadGitStatus(); break;
        }
    },

    // ─── API Helpers ────────────────────────────────────────────

    async api(path, options = {}) {
        try {
            const url = `${API_BASE}${path}`;
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
            if (response.status === 204) return null;
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
            dot.className = `status-dot ${data.status === 'healthy' ? 'online' : 'offline'}`;
        } catch {
            const dot = document.querySelector('#server-status .status-dot');
            dot.className = 'status-dot offline';
        }
    },

    connectWebSocket() {
        try {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            this.ws = new WebSocket(`${protocol}//${location.host}/ws/progress`);
            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'stage_update') {
                    this.refresh();
                }
            };
            this.ws.onclose = () => {
                setTimeout(() => this.connectWebSocket(), 5000);
            };
        } catch (e) {
            console.log('WebSocket not available, using polling');
        }
    },

    refresh() {
        this.switchPage(this.currentPage);
    },

    // ─── Dashboard ──────────────────────────────────────────────

    async loadDashboard() {
        try {
            const [summary, overview, activity] = await Promise.all([
                this.api('/dashboard/summary'),
                this.api('/dashboard/designs-overview').catch(() => []),
                this.api('/dashboard/activity').catch(() => []),
            ]);

            document.getElementById('stat-designs').textContent = summary.total_designs;
            document.getElementById('stat-active').textContent = summary.active_designs;
            document.getElementById('stat-stages').textContent = summary.total_stages_run;
            document.getElementById('stat-passing').textContent = summary.passing_stages;
            document.getElementById('stat-failing').textContent = summary.failing_stages;
            document.getElementById('stat-scripts').textContent = summary.total_scripts;

            this.renderDesignsOverview(overview);
            this.renderActivity(activity);
        } catch (err) {
            console.error('Dashboard load failed:', err);
        }
    },

    renderDesignsOverview(designs) {
        const tbody = document.getElementById('designs-table-body');
        if (!designs || designs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="empty">No designs yet.</td></tr>';
            return;
        }
        tbody.innerHTML = designs.map(d => `
            <tr onclick="App.switchPage('stages')">
                <td><strong>${this.esc(d.name)}</strong></td>
                <td><span class="badge badge-${d.status}">${d.status}</span></td>
                <td>${this.esc(d.pdk || '-')}</td>
                <td>${d.clock_period_ns}</td>
                <td>${d.latest_metrics?.wns ?? '-'}</td>
                <td>${d.latest_metrics?.tns ?? '-'}</td>
                <td>${d.latest_metrics?.drc_errors ?? '-'}</td>
                <td>${this.formatDate(d.updated_at)}</td>
            </tr>
        `).join('');
    },

    renderActivity(activities) {
        const container = document.getElementById('activity-feed');
        if (!activities || activities.length === 0) {
            container.innerHTML = '<div class="empty">No recent activity</div>';
            return;
        }
        container.innerHTML = activities.slice(0, 10).map(a => `
            <div class="activity-item">
                <span class="activity-type">${a.type}</span>
                <span>${this.esc(a.message)}</span>
                <span class="activity-time">${this.formatDate(a.timestamp)}</span>
            </div>
        `).join('');
    },

    // ─── Designs ────────────────────────────────────────────────

    async loadDesignsList() {
        try {
            const designs = await this.api('/designs');
            const container = document.getElementById('designs-list');
            if (designs.length === 0) {
                container.innerHTML = '<div class="empty">No designs. Create one to get started.</div>';
                return;
            }
            container.innerHTML = designs.map(d => `
                <div class="design-card" onclick="App.viewDesign(${d.id})">
                    <h4>${this.esc(d.name)}</h4>
                    <span class="badge badge-${d.status}">${d.status}</span>
                    <div class="meta">
                        <span>Module: ${this.esc(d.top_module)}</span>
                        <span>PDK: ${this.esc(d.pdk_name || '-')}</span>
                        <span>Clock: ${d.clock_period_ns}ns</span>
                        <span>Stages: ${d.stage_count}</span>
                    </div>
                </div>
            `).join('');
        } catch (err) {
            console.error('Failed to load designs:', err);
        }
    },

    async populateDesignSelect(selectId) {
        try {
            const designs = await this.api('/designs');
            const select = document.getElementById(selectId);
            const current = select.value;
            select.innerHTML = '<option value="">Select Design...</option>';
            designs.forEach(d => {
                select.innerHTML += `<option value="${d.id}">${this.esc(d.name)}</option>`;
            });
            if (current) select.value = current;
        } catch (err) {
            console.error('Failed to populate select:', err);
        }
    },

    showCreateDesign() {
        document.getElementById('modal-create-design').classList.remove('hidden');
    },

    async createDesign(event) {
        event.preventDefault();
        const form = event.target;
        const data = {
            name: form.name.value,
            top_module: form.top_module.value,
            pdk_name: form.pdk_name.value,
            clock_period_ns: parseFloat(form.clock_period_ns.value),
            target_utilization: parseFloat(form.target_utilization.value),
            config_path: form.config_path.value,
            description: form.description.value,
        };
        try {
            await this.api('/designs', { method: 'POST', body: data });
            this.closeModal('modal-create-design');
            form.reset();
            this.loadDesignsList();
        } catch (err) {
            alert(`Failed to create design: ${err.message}`);
        }
    },

    async viewDesign(designId) {
        this.switchPage('stages');
        document.getElementById('stage-design-select').value = designId;
        this.loadStages();
    },

    // ─── Stages ─────────────────────────────────────────────────

    async loadStages() {
        const designId = document.getElementById('stage-design-select').value;
        if (!designId) return;

        try {
            const [stages, flowStatus] = await Promise.all([
                this.api(`/stages/${designId}`),
                this.api(`/stages/${designId}/flow-status`),
            ]);

            this.renderFlowPipeline(flowStatus);
            this.renderStagesTable(stages);
        } catch (err) {
            console.error('Failed to load stages:', err);
        }
    },

    renderFlowPipeline(flowStatus) {
        const stages = flowStatus.stage_details || [];
        const stageMap = {};
        stages.forEach(s => { stageMap[s.stage_name] = s; });

        document.querySelectorAll('.flow-stage').forEach(el => {
            const name = el.dataset.stage;
            const stage = stageMap[name];

            el.className = 'flow-stage';
            const statusEl = el.querySelector('.stage-status');

            if (stage) {
                el.classList.add(stage.status);
                statusEl.textContent = stage.status.charAt(0).toUpperCase() + stage.status.slice(1);
            } else {
                el.classList.add('pending');
                statusEl.textContent = 'Pending';
            }
        });
    },

    renderStagesTable(stages) {
        const tbody = document.getElementById('stages-table-body');
        if (!stages || stages.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="empty">No stages run yet</td></tr>';
            return;
        }
        tbody.innerHTML = stages.map(s => `
            <tr>
                <td><strong>${this.esc(s.stage_name)}</strong></td>
                <td>${this.esc(s.tool || '-')}</td>
                <td><span class="badge badge-${s.status}">${s.status}</span></td>
                <td>${s.elapsed_seconds ? s.elapsed_seconds.toFixed(1) + 's' : '-'}</td>
                <td>${s.timing?.wns ?? '-'}</td>
                <td>${s.timing?.tns ?? '-'}</td>
                <td>${this.formatDate(s.created_at)}</td>
                <td>
                    ${s.log_file ? `<button class="btn btn-sm" onclick="App.viewStageLog(${s.id})">Log</button>` : ''}
                </td>
            </tr>
        `).join('');
    },

    async viewStageLog(stageId) {
        try {
            const stage = await this.api(`/stages/detail/${stageId}`);
            const designId = stage.design_id;
            const logData = await this.api(`/stages/${designId}/log/${stage.stage_name}`);
            document.getElementById('log-content').textContent = logData.content || 'No log content';
            document.getElementById('log-status').textContent = stage.status;
            document.getElementById('log-status').className = `badge badge-${stage.status}`;
            document.getElementById('modal-execution-log').classList.remove('hidden');
        } catch (err) {
            alert('Failed to load log: ' + err.message);
        }
    },

    // ─── Metrics ────────────────────────────────────────────────

    async loadMetrics() {
        const designId = document.getElementById('metrics-design-select').value;
        if (!designId) return;

        try {
            const [metrics, trends] = await Promise.all([
                this.api(`/metrics/${designId}`),
                this.api(`/metrics/${designId}/trends`),
            ]);

            this.renderMetricsTable(metrics);
            this.renderCharts(trends);
        } catch (err) {
            console.error('Failed to load metrics:', err);
        }
    },

    renderMetricsTable(metrics) {
        const tbody = document.getElementById('metrics-table-body');
        if (!metrics || metrics.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="empty">No metrics recorded</td></tr>';
            return;
        }
        tbody.innerHTML = metrics.map(m => `
            <tr>
                <td>${m.iteration}</td>
                <td class="${m.wns !== null && m.wns >= 0 ? 'text-success' : 'text-danger'}">${m.wns ?? '-'}</td>
                <td>${m.tns ?? '-'}</td>
                <td>${m.utilization !== null ? (m.utilization * 100).toFixed(1) + '%' : '-'}</td>
                <td>${m.total_power_mw ?? '-'}</td>
                <td>${m.drc_errors ?? '-'}</td>
                <td>${m.num_violating_paths ?? '-'}</td>
                <td>${this.formatDate(m.snapshot_at)}</td>
            </tr>
        `).join('');
    },

    renderCharts(trends) {
        const labels = trends.iterations.map(i => `#${i}`);
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: true,
            plugins: { legend: { labels: { color: '#9ca3af' } } },
            scales: {
                x: { ticks: { color: '#6b7280' }, grid: { color: '#2d3348' } },
                y: { ticks: { color: '#6b7280' }, grid: { color: '#2d3348' } },
            },
        };

        // Timing chart
        this._updateChart('chart-timing', {
            labels,
            datasets: [
                { label: 'WNS (ns)', data: trends.wns, borderColor: '#3b82f6', tension: 0.3 },
                { label: 'TNS (ns)', data: trends.tns, borderColor: '#ef4444', tension: 0.3 },
            ],
        }, chartOptions);

        // Power chart
        this._updateChart('chart-power', {
            labels,
            datasets: [
                { label: 'Total Power (mW)', data: trends.total_power_mw, borderColor: '#f59e0b', tension: 0.3 },
                { label: 'Leakage (mW)', data: trends.leakage_power_mw, borderColor: '#8b5cf6', tension: 0.3 },
            ],
        }, chartOptions);

        // Utilization chart
        this._updateChart('chart-utilization', {
            labels,
            datasets: [
                { label: 'Utilization (%)', data: trends.utilization.map(v => v !== null ? v * 100 : null), borderColor: '#10b981', tension: 0.3, fill: true, backgroundColor: 'rgba(16,185,129,0.1)' },
            ],
        }, chartOptions);

        // DRC chart
        this._updateChart('chart-drc', {
            labels,
            datasets: [
                { label: 'DRC Errors', data: trends.drc_errors, borderColor: '#ef4444', tension: 0.3, fill: true, backgroundColor: 'rgba(239,68,68,0.1)' },
                { label: 'Violating Paths', data: trends.num_violating_paths, borderColor: '#f59e0b', tension: 0.3 },
            ],
        }, chartOptions);
    },

    _updateChart(canvasId, data, options) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        if (this.charts[canvasId]) {
            this.charts[canvasId].data = data;
            this.charts[canvasId].update();
        } else {
            this.charts[canvasId] = new Chart(canvas, {
                type: 'line',
                data,
                options: { ...options, elements: { point: { radius: 4 } } },
            });
        }
    },

    // ─── Scripts ────────────────────────────────────────────────

    async loadScripts() {
        const designId = document.getElementById('scripts-design-select').value;
        if (!designId) return;

        try {
            const scripts = await this.api(`/scripts/${designId}`);
            this.renderScriptsTable(scripts);
        } catch (err) {
            console.error('Failed to load scripts:', err);
        }
    },

    renderScriptsTable(scripts) {
        const tbody = document.getElementById('scripts-table-body');
        if (!scripts || scripts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="empty">No scripts generated</td></tr>';
            return;
        }
        tbody.innerHTML = scripts.map(s => `
            <tr>
                <td>#${s.id}</td>
                <td>${this.esc(s.stage_name)}</td>
                <td><code>${this.esc(s.filename)}</code></td>
                <td>${s.script_type}</td>
                <td><span class="badge badge-${s.status}">${s.status}</span></td>
                <td>${s.exit_code !== null ? s.exit_code : '-'}</td>
                <td>${this.formatDate(s.generated_at)}</td>
                <td>
                    <button class="btn btn-sm" onclick="App.previewScript(${s.id})">Preview</button>
                    ${s.status === 'generated' ? `<button class="btn btn-sm btn-primary" onclick="App.confirmExecute(${s.id})">Run</button>` : ''}
                    ${s.execution_log ? `<button class="btn btn-sm" onclick="App.viewExecLog(${s.id})">Log</button>` : ''}
                </td>
            </tr>
        `).join('');
    },

    showGenerateScript() {
        const designId = document.getElementById('scripts-design-select').value;
        if (!designId) {
            alert('Please select a design first');
            return;
        }
        document.getElementById('modal-generate-script').classList.remove('hidden');
    },

    async generateScript(event) {
        event.preventDefault();
        const form = event.target;
        const designId = document.getElementById('scripts-design-select').value;
        const data = {
            design_id: parseInt(designId),
            stage_name: form.stage_name.value,
            content: form.content.value,
            filename: form.filename.value,
            script_type: form.filename.value.endsWith('.py') ? 'python' : 'tcl',
        };
        try {
            const result = await this.api('/scripts/generate', { method: 'POST', body: data });
            this.closeModal('modal-generate-script');
            this.loadScripts();
            this.previewScript(result.id);
        } catch (err) {
            alert('Failed to generate script: ' + err.message);
        }
    },

    async previewScript(scriptId) {
        try {
            const data = await this.api(`/scripts/preview/${scriptId}`);
            document.getElementById('preview-filename').textContent = data.filename;
            document.getElementById('preview-status').textContent = data.status;
            document.getElementById('preview-status').className = `badge badge-${data.status}`;
            document.getElementById('preview-content').textContent = data.preview_content || data.content;
            this.currentScriptId = scriptId;
            document.getElementById('modal-script-preview').classList.remove('hidden');
        } catch (err) {
            alert('Failed to load preview: ' + err.message);
        }
    },

    async confirmExecute(scriptId) {
        if (!confirm('Execute this script? This will launch the EDA tool.')) return;
        this.executeScriptById(scriptId, true);
    },

    async executeScript(confirmed) {
        if (!this.currentScriptId) return;
        if (confirmed && !confirm('Confirm execution? This will launch the EDA tool.')) return;
        this.executeScriptById(this.currentScriptId, confirmed);
    },

    async executeScriptById(scriptId, confirmed) {
        try {
            const result = await this.api('/scripts/execute', {
                method: 'POST',
                body: { script_id: scriptId, confirmed },
            });
            if (!confirmed) {
                alert('Set confirmed to execute. Currently: ' + result.status);
                return;
            }
            this.closeModal('modal-script-preview');
            this.loadScripts();
            if (result.execution_log) {
                this.showExecLog(scriptId, result);
            }
        } catch (err) {
            alert('Execution failed: ' + err.message);
        }
    },

    async viewExecLog(scriptId) {
        try {
            const log = await this.api(`/scripts/log/${scriptId}`);
            this.showExecLog(scriptId, log);
        } catch (err) {
            alert('Failed to load log: ' + err.message);
        }
    },

    showExecLog(scriptId, data) {
        document.getElementById('log-status').textContent = data.status || 'unknown';
        document.getElementById('log-status').className = `badge badge-${data.status || 'pending'}`;
        document.getElementById('log-exit-code').textContent = data.exit_code !== null ? `Exit: ${data.exit_code}` : '';
        document.getElementById('log-content').textContent = data.execution_log || data.log || 'No log available';
        document.getElementById('modal-execution-log').classList.remove('hidden');
    },

    // ─── Git ────────────────────────────────────────────────────

    async loadGitStatus() {
        try {
            const [status, log] = await Promise.all([
                this.api('/git/status'),
                this.api('/git/log?count=20'),
            ]);

            document.getElementById('git-current-branch').textContent = status.branch;
            document.getElementById('git-clean-status').textContent =
                status.is_clean ? '✓ Working tree clean' : '⚠ Uncommitted changes';

            this.renderGitStatus(status);
            this.renderGitLog(log);
        } catch (err) {
            document.getElementById('git-current-branch').textContent = 'N/A';
            document.getElementById('git-clean-status').textContent = 'Git not configured';
            console.error('Git status failed:', err);
        }
    },

    renderGitStatus(status) {
        const renderFileList = (files, containerId, statusClass) => {
            const container = document.getElementById(containerId);
            if (!files || files.length === 0) {
                container.innerHTML = '<div class="empty">None</div>';
                return;
            }
            container.innerHTML = files.map(f => {
                const name = typeof f === 'string' ? f : f.path;
                const st = typeof f === 'string' ? 'untracked' : f.status;
                return `
                    <div class="file-item">
                        <span class="file-status file-status-${st}">${st.charAt(0).toUpperCase()}</span>
                        <span>${this.esc(name)}</span>
                    </div>
                `;
            }).join('');
        };

        renderFileList(status.staged, 'git-staged');
        renderFileList(status.unstaged, 'git-unstaged');
        renderFileList(status.untracked, 'git-untracked');
    },

    renderGitLog(commits) {
        const tbody = document.getElementById('git-log-body');
        if (!commits || commits.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty">No commits</td></tr>';
            return;
        }
        tbody.innerHTML = commits.map(c => `
            <tr>
                <td><code>${this.esc(c.short_hash)}</code></td>
                <td>${this.esc(c.author)}</td>
                <td>${this.esc(c.message)}</td>
                <td>+${c.insertions} -${c.deletions}</td>
                <td>${this.formatDate(c.committed_at)}</td>
            </tr>
        `).join('');
    },

    showCommitModal() {
        document.getElementById('modal-commit').classList.remove('hidden');
    },

    async gitCommit(event) {
        event.preventDefault();
        const message = event.target.message.value;
        try {
            const result = await this.api('/git/commit', {
                method: 'POST',
                body: { repo_path: '', action: 'commit', message, files: [] },
            });
            this.closeModal('modal-commit');
            event.target.reset();
            this.loadGitStatus();
            alert(result.status === 'committed' ? `Committed: ${result.short_hash}` : result.message);
        } catch (err) {
            alert('Commit failed: ' + err.message);
        }
    },

    // ─── Utilities ──────────────────────────────────────────────

    closeModal(modalId) {
        document.getElementById(modalId).classList.add('hidden');
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
        return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    },
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => App.init());
