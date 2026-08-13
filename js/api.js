/**
 * BotForge API client — handles all communication with the FastAPI backend.
 */
const API_BASE = 'https://botforge-production.up.railway.app/api';
const api = {
    // ── Helpers ──────────────────────────────────────
    _token() {
        return localStorage.getItem('botforge_token');
    },
    _headers(json = true) {
        const h = {};
        if (json) h['Content-Type'] = 'application/json';
        const token = this._token();
        if (token) h['Authorization'] = `Bearer ${token}`;
        return h;
    },
    async _request(method, path, body = null) {
        const opts = { method, headers: this._headers() };
        if (body) opts.body = JSON.stringify(body);
        const res = await fetch(`${API_BASE}${path}`, opts);
        if (res.status === 204) return null;
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
        return data;
    },
    // ── Auth ─────────────────────────────────────────
    async signup(name, email, password) {
        const data = await this._request('POST', '/auth/signup', { name, email, password });
        localStorage.setItem('botforge_token', data.access_token);
        return data;
    },
    async login(email, password) {
        const data = await this._request('POST', '/auth/login', { email, password });
        localStorage.setItem('botforge_token', data.access_token);
        return data;
    },
    logout() {
        localStorage.removeItem('botforge_token');
        window.location.href = '../index.html';
    },
    async getMe() {
        return this._request('GET', '/auth/me');
    },
    // ── Bots ─────────────────────────────────────────
    async listBots() {
        return this._request('GET', '/bots');
    },
    async createBot(config) {
        return this._request('POST', '/bots', config);
    },
    async getBot(botId) {
        return this._request('GET', `/bots/${botId}`);
    },
    async updateBot(botId, config) {
        return this._request('PUT', `/bots/${botId}`, config);
    },
    async deleteBot(botId) {
        return this._request('DELETE', `/bots/${botId}`);
    },
    // ── Bot Control ──────────────────────────────────
    async startBot(botId) {
        return this._request('POST', `/bots/${botId}/start`);
    },
    async stopBot(botId) {
        return this._request('POST', `/bots/${botId}/stop`);
    },
    async restartBot(botId) {
        return this._request('POST', `/bots/${botId}/restart`);
    },
    // ── Stats ────────────────────────────────────────
    async getStats() {
        return this._request('GET', '/stats');
    },
    // ── Billing ──────────────────────────────────────
    async getBillingStatus() {
        return this._request('GET', '/billing/status');
    },
    async createCheckout(plan) {
        return this._request('POST', '/billing/checkout', { plan });
    },
    async upgradeTo(plan) {
        const { checkout_url } = await this.createCheckout(plan);
        window.location.href = checkout_url;
    },
};
// Export for use in pages
window.api = api;
