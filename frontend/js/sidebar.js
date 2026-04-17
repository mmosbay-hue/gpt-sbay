/* Sidebar — conversation list management (SbayAI-style) */
const Sidebar = {
    currentConvId: null,

    async load() {
        const res = await fetch('/api/conversations');
        const convs = await res.json();
        this.renderList(convs);
    },

    renderList(convs) {
        const list = document.getElementById('conversationList');
        list.innerHTML = '';

        const today = new Date().toDateString();
        const yesterday = new Date(Date.now() - 86400000).toDateString();
        const groups = {};

        convs.forEach(c => {
            const date = new Date(c.created_at).toDateString();
            let label;
            if (date === today) label = 'Today';
            else if (date === yesterday) label = 'Yesterday';
            else label = new Date(c.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

            if (!groups[label]) groups[label] = [];
            groups[label].push(c);
        });

        // Sort: Today first, Yesterday second, then by date descending
        const sortedLabels = Object.keys(groups).sort((a, b) => {
            if (a === 'Today') return -1;
            if (b === 'Today') return 1;
            if (a === 'Yesterday') return -1;
            if (b === 'Yesterday') return 1;
            return new Date(b) - new Date(a);
        });

        sortedLabels.forEach(label => {
            const groupEl = document.createElement('div');
            groupEl.className = 'conv-date-group';
            groupEl.textContent = label;
            list.appendChild(groupEl);

            groups[label]
                .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
                .forEach(c => {
                    const el = document.createElement('div');
                    el.className = 'conv-item' + (c.id === this.currentConvId ? ' active' : '');
                    el.textContent = c.title || 'New chat';
                    el.onclick = () => this.select(c.id);

                    // Double-click to rename
                    el.ondblclick = (e) => {
                        e.stopPropagation();
                        const newTitle = prompt('Đổi tên:', c.title);
                        if (newTitle && newTitle.trim()) this.rename(c.id, newTitle.trim());
                    };

                    const delBtn = document.createElement('button');
                    delBtn.className = 'delete-btn';
                    delBtn.innerHTML = '&times;';
                    delBtn.onclick = (e) => {
                        e.stopPropagation();
                        this.delete(c.id);
                    };
                    el.appendChild(delBtn);
                    list.appendChild(el);
                });
        });
    },

    async select(convId) {
        this.currentConvId = convId;
        const res = await fetch(`/api/conversations/${convId}`);
        const conv = await res.json();
        Chat.loadConversation(conv);
        this.load();
    },

    async delete(convId) {
        await fetch(`/api/conversations/${convId}`, { method: 'DELETE' });
        if (convId === this.currentConvId) {
            this.currentConvId = null;
            Chat.clear();
        }
        this.load();
    },

    async rename(convId, newTitle) {
        // Update title via API (PATCH not available, use conversation update)
        // For now update client-side by re-fetching
        await fetch(`/api/conversations/${convId}/rename?title=${encodeURIComponent(newTitle)}`, { method: 'POST' });
        this.load();
    },

    newChat() {
        this.currentConvId = null;
        Chat.clear();
    }
};
