/**
 * Creates a debounced function that delays invoking func until after wait milliseconds have elapsed
 * since the last time the debounced function was invoked.
 * @param {Function} func The function to debounce
 * @param {number} wait The number of milliseconds to delay
 * @returns {Function} The debounced function
 */
function debounce(func, wait) {
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

/**
 * Formats a number with commas as thousands separators
 * @param {number} num The number to format
 * @returns {string} The formatted number
 */
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/**
 * Truncates a string to a specified length and adds an ellipsis if truncated
 * @param {string} str The string to truncate
 * @param {number} length The maximum length
 * @returns {string} The truncated string
 */
function truncateString(str, length) {
    if (!str) return '';
    if (str.length <= length) return str;
    return str.slice(0, length) + '...';
}

/**
 * Safely gets a nested object property using a path string
 * @param {Object} obj The object to get the property from
 * @param {string} path The property path (e.g., 'user.address.city')
 * @param {*} defaultValue The default value if the path doesn't exist
 * @returns {*} The property value or default value
 */
function getNestedValue(obj, path, defaultValue = null) {
    return path.split('.').reduce((current, key) => 
        (current && current[key] !== undefined) ? current[key] : defaultValue, obj);
}

/**
 * Escapes HTML special characters in a string
 * @param {string} str The string to escape
 * @returns {string} The escaped string
 */
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

/**
 * Checks if a value is empty (null, undefined, empty string, empty array, or empty object)
 * @param {*} value The value to check
 * @returns {boolean} True if the value is empty
 */
function isEmpty(value) {
    if (value === null || value === undefined) return true;
    if (typeof value === 'string') return value.trim().length === 0;
    if (Array.isArray(value)) return value.length === 0;
    if (typeof value === 'object') return Object.keys(value).length === 0;
    return false;
} 