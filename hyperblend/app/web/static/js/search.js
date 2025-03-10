// hyperblend/app/web/static/js/search.js

class GlobalSearch {
    constructor(element) {
        if (!element) {
            console.warn('Search container element not found');
            return;
        }
        
        this.element = element;
        this.searchInput = element.querySelector('input[type="search"]');
        this.searchResults = element.querySelector('.search-results');
        
        if (!this.searchInput || !this.searchResults) {
            console.warn('Required search elements not found');
            return;
        }
        
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        if (!this.searchInput) return;
        
        this.searchInput.addEventListener('input', this.debounce((e) => {
            this.handleSearch(e.target.value);
        }, 300));
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    async handleSearch(query) {
        if (!query) {
            this.hideResults();
            return;
        }

        try {
            const response = await fetch(`/api/molecules/search?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            this.showResults(data);
        } catch (error) {
            console.error('Search error:', error);
            this.showError('Error performing search');
        }
    }

    showResults(results) {
        if (!this.searchResults) return;
        
        if (!results.length) {
            this.searchResults.innerHTML = '<div class="p-4 text-gray-500">No results found</div>';
        } else {
            this.searchResults.innerHTML = results
                .map(result => this.renderSearchResult(result))
                .join('');
        }
        this.searchResults.classList.remove('hidden');
    }

    renderSearchResult(result) {
        return `
            <div class="p-2 hover:bg-gray-100 cursor-pointer" onclick="window.location.href='/molecules/${result.id}'">
                <div class="font-medium">${result.name}</div>
                <div class="text-sm text-gray-600">${result.formula || ''}</div>
            </div>
        `;
    }

    hideResults() {
        if (this.searchResults) {
            this.searchResults.classList.add('hidden');
        }
    }

    showError(message) {
        if (this.searchResults) {
            this.searchResults.innerHTML = `<div class="p-4 text-red-500">${message}</div>`;
            this.searchResults.classList.remove('hidden');
        }
    }
} 