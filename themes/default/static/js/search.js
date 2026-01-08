(function() {
    const modal = document.getElementById('searchModal');
    if (!modal) {
        return;
    }

    const backdrop = document.getElementById('searchBackdrop');
    const closeBtn = document.getElementById('searchClose');
    const toggleBtn = document.getElementById('searchToggle');
    const input = document.getElementById('searchInput');
    const loading = document.getElementById('searchLoading');
    const resultsList = document.getElementById('searchResultsList');
    const emptyState = document.getElementById('searchEmpty');
    const noResults = document.getElementById('searchNoResults');
    const configEl = document.getElementById('searchConfig');

    const typePage = configEl?.dataset?.typePage || 'Page';
    const typeBlog = configEl?.dataset?.typeBlog || 'Post';

    let searchTimeout = null;
    let activeIndex = -1;
    let results = [];

    function openSearch() {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
        setTimeout(() => input.focus(), 100);
    }

    function closeSearch() {
        modal.classList.remove('active');
        document.body.style.overflow = '';
        input.value = '';
        resultsList.innerHTML = '';
        emptyState.style.display = 'block';
        noResults.style.display = 'none';
        activeIndex = -1;
        results = [];
    }

    function setLoading(show) {
        loading.classList.toggle('active', show);
    }

    function renderResults(data) {
        results = data.results || [];
        resultsList.innerHTML = '';
        emptyState.style.display = 'none';
        noResults.style.display = 'none';

        if (results.length === 0) {
            noResults.style.display = 'block';
            return;
        }

        results.forEach((item, index) => {
            const a = document.createElement('a');
            a.href = item.url;
            a.className = 'search-result-item';
            a.dataset.index = index;

            const iconClass = item.type === 'page' ? 'page' : 'blog';
            const icon = item.type === 'page'
                ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>'
                : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>';

            const typeLabel = item.type === 'page' ? typePage : typeBlog;

            a.innerHTML = `
                <div class="search-result-icon ${iconClass}">${icon}</div>
                <div class="search-result-content">
                    <div class="search-result-title">${item.title_highlighted}</div>
                    <div class="search-result-excerpt">${item.excerpt_highlighted}</div>
                    <div class="search-result-meta">
                        <span class="search-result-type">${typeLabel}</span>
                        ${item.category ? ' · ' + item.category : ''}
                    </div>
                </div>
            `;

            resultsList.appendChild(a);
        });

        activeIndex = -1;
    }

    function updateActiveResult() {
        const items = resultsList.querySelectorAll('.search-result-item');
        items.forEach((item, i) => {
            item.classList.toggle('active', i === activeIndex);
        });
        if (activeIndex >= 0 && items[activeIndex]) {
            items[activeIndex].scrollIntoView({ block: 'nearest' });
        }
    }

    async function performSearch(query) {
        if (query.length < 2) {
            resultsList.innerHTML = '';
            emptyState.style.display = 'block';
            noResults.style.display = 'none';
            return;
        }

        setLoading(true);
        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=10`);
            const data = await response.json();
            renderResults(data);
        } catch (err) {
            console.error('Search error:', err);
            noResults.style.display = 'block';
            emptyState.style.display = 'none';
        } finally {
            setLoading(false);
        }
    }

    if (toggleBtn) {
        toggleBtn.addEventListener('click', openSearch);
    }
    backdrop?.addEventListener('click', closeSearch);
    closeBtn?.addEventListener('click', closeSearch);

    input?.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            performSearch(e.target.value.trim());
        }, 300);
    });

    input?.addEventListener('keydown', (e) => {
        const items = resultsList.querySelectorAll('.search-result-item');

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            activeIndex = Math.min(activeIndex + 1, items.length - 1);
            updateActiveResult();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            activeIndex = Math.max(activeIndex - 1, -1);
            updateActiveResult();
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (activeIndex >= 0 && items[activeIndex]) {
                items[activeIndex].click();
            }
        } else if (e.key === 'Escape') {
            closeSearch();
        }
    });

    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            openSearch();
        }
        if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
            e.preventDefault();
            openSearch();
        }
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            closeSearch();
        }
    });
})();
