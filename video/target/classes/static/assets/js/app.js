const app = {
    tokenKey: "video_portal_token",
    userKey: "video_portal_user",
    videoCardContexts: {},

    getToken() {
        return localStorage.getItem(this.tokenKey) || "";
    },

    getUser() {
        const raw = localStorage.getItem(this.userKey);
        return raw ? JSON.parse(raw) : null;
    },

    saveSession(data) {
        localStorage.setItem(this.tokenKey, data.token);
        localStorage.setItem(this.userKey, JSON.stringify(data.user));
    },

    clearSession() {
        localStorage.removeItem(this.tokenKey);
        localStorage.removeItem(this.userKey);
    },

    async request(url, options = {}) {
        const isFormData = options.body instanceof FormData;
        const headers = {
            ...(isFormData ? {} : { "Content-Type": "application/json" }),
            ...(options.headers || {})
        };
        const token = this.getToken();
        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }
        const response = await fetch(url, {
            ...options,
            headers
        });
        const result = await response.json();
        if (!result.success) {
            throw new Error(result.message || "请求失败");
        }
        return result.data;
    },

    ensureLogin() {
        if (!this.getToken()) {
            location.href = "/user/login.html";
            return false;
        }
        return true;
    },

    ensureAdmin() {
        const user = this.getUser();
        if (!user || (user.role !== "ADMIN" && user.role !== "SUPER_ADMIN")) {
            location.href = "/admin/login.html";
            return false;
        }
        return true;
    },

    logout(target = "/user/login.html") {
        this.clearSession();
        location.href = target;
    },

    renderVideoCards(list, targetId, options = {}) {
        const container = document.getElementById(targetId);
        if (!container) return;
        const records = Array.isArray(list) ? list.map(item => ({ ...item })) : [];
        const context = {
            records,
            refresh: typeof options.refresh === "function" ? options.refresh : null
        };
        this.videoCardContexts[targetId] = context;
        container.innerHTML = records.map(item => `
            <div class="video-card" data-video-card data-video-id="${item.id}">
                <div class="video-card-cover-wrapper">
                    <img src="${item.coverUrl || ''}" alt="${item.title}">
                </div>
                <div class="video-card-content">
                    <h3>${item.title}</h3>
                    <div class="meta">${item.sourcePlatform || "未设置"} · ${item.playCount || 0}次播放</div>
                    <div class="video-card-actions">
                        <button type="button" class="video-card-action ${item.liked ? "active" : ""}" data-video-action="like" data-video-id="${item.id}">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
                            <span>${item.likeCount || 0}</span>
                        </button>
                        <button type="button" class="video-card-action ${item.favorited ? "active" : ""}" data-video-action="favorite" data-video-id="${item.id}">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M17 3H7c-1.1 0-1.99.9-1.99 2L5 21l7-3 7 3V5c0-1.1-.9-2-2-2z"/></svg>
                            <span>${item.favoriteCount || 0}</span>
                        </button>
                    </div>
                    <div class="tags">${(item.tags || []).slice(0,3).map(tag => `<span class="tag">${tag}</span>`).join("")}</div>
                </div>
            </div>
        `).join("");
        container.querySelectorAll("[data-video-card]").forEach(card => {
            card.addEventListener("click", () => {
                location.href = `/user/detail.html?id=${card.dataset.videoId}`;
            });
        });
        container.querySelectorAll("[data-video-action]").forEach(button => {
            button.addEventListener("click", (event) => this.handleVideoCardAction(event, targetId));
        });
    },

    async handleVideoCardAction(event, targetId) {
        event.stopPropagation();
        const button = event.currentTarget;
        const videoId = Number(button.dataset.videoId);
        const action = button.dataset.videoAction;
        if (!videoId || !action) {
            return;
        }
        if (!this.ensureLogin()) {
            return;
        }
        button.disabled = true;
        try {
            const result = await this.request(`/api/video/${videoId}/${action}`, { method: "POST" });
            const context = this.videoCardContexts[targetId];
            if (!context) {
                return;
            }
            const target = context.records.find(item => Number(item.id) === videoId);
            if (target) {
                if (action === "like") {
                    target.liked = !!result.liked;
                    target.likeCount = Number(result.likeCount ?? target.likeCount ?? 0);
                } else {
                    target.favorited = !!result.favorited;
                    target.favoriteCount = Number(result.favoriteCount ?? target.favoriteCount ?? 0);
                }
            }
            if (context.refresh) {
                await context.refresh();
                return;
            }
            this.renderVideoCards(context.records, targetId);
        } catch (error) {
            alert(error.message);
        } finally {
            button.disabled = false;
        }
    },

    renderPager(targetId, pageData, onChange) {
        const container = document.getElementById(targetId);
        if (!container || !pageData) return;
        const page = Number(pageData.page || 1);
        const totalPages = Number(pageData.totalPages || 1);
        const total = Number(pageData.total || 0);
        container.innerHTML = `
            <div class="app-pagination">
                <span class="pager-info">第 ${page} / ${totalPages || 1} 页，共 ${total} 条</span>
                <div class="app-pagination-controls">
                    <button class="app-btn app-btn-ghost" ${page <= 1 ? "disabled" : ""} id="${targetId}-prev">上一页</button>
                    <div class="pager-jump">
                        <span>跳至</span>
                        <input type="number" class="pager-jump-input" id="${targetId}-jump-input" min="1" max="${totalPages || 1}" placeholder="${page}">
                        <span>页</span>
                        <button class="app-btn app-btn-ghost app-btn-sm" id="${targetId}-jump-btn">GO</button>
                    </div>
                    <button class="app-btn app-btn-ghost" ${page >= totalPages ? "disabled" : ""} id="${targetId}-next">下一页</button>
                </div>
            </div>
        `;
        const prev = document.getElementById(`${targetId}-prev`);
        const next = document.getElementById(`${targetId}-next`);
        const jumpInput = document.getElementById(`${targetId}-jump-input`);
        const jumpBtn = document.getElementById(`${targetId}-jump-btn`);
        if (prev) {
            prev.addEventListener("click", () => {
                if (page > 1) onChange(page - 1);
            });
        }
        if (next) {
            next.addEventListener("click", () => {
                if (page < totalPages) onChange(page + 1);
            });
        }
        if (jumpInput && jumpBtn) {
            const doJump = () => {
                const targetPage = parseInt(jumpInput.value, 10);
                if (targetPage && targetPage >= 1 && targetPage <= totalPages && targetPage !== page) {
                    onChange(targetPage);
                }
            };
            jumpBtn.addEventListener("click", doJump);
            jumpInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter") doJump();
            });
        }
    },

    fillUserNav(prefix = "/user/login.html") {
        const el = document.getElementById("user-nav");
        if (!el) return;
        const user = this.getUser();
        el.innerHTML = user
            ? `<div class="account-actions">
                    <div class="account-chip">
                        <img class="account-chip__avatar" src="${user.avatarUrl || '/assets/img/default-avatar.png'}" alt="Avatar" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\\'http://www.w3.org/2000/svg\\' viewBox=\\'0 0 24 24\\' fill=\\'%23cbd5e1\\'%3E%3Cpath d=\\'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z\\'/%3E%3C/svg%3E'">
                        <div class="account-chip__meta">
                            <strong>${user.realName || user.username}</strong>
                            <span>${user.role}</span>
                        </div>
                    </div>
                    <button class="app-btn app-btn-ghost app-btn-sm" onclick="app.logout('${prefix}')">退出</button>
               </div>`
            : `<div class="account-actions">
                    <a class="app-btn app-btn-ghost app-btn-sm" href="/user/login.html">登录</a>
                    <a class="app-btn app-btn-dark app-btn-sm" href="/user/register.html">注册</a>
               </div>`;
    }
};
