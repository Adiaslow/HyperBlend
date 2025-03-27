/**
 * List utilities - Common functions for handling list items across all entity types
 */

/**
 * Add click event listeners to list items when they are in the DOM
 * This function can be used by any page that displays a list of items
 */
function attachListItemEventListeners() {
    console.log('Attaching list item event listeners');
    // Find all list items using a generic class that can be used across all listing pages
    const listItems = document.querySelectorAll('.list-item-card');
    
    if (listItems.length === 0) {
        console.warn('No list items found on the page');
    } else {
        console.log(`Found ${listItems.length} list items`);
    }
    
    listItems.forEach(item => {
        // Remove any existing click event to avoid duplicates
        item.removeEventListener('click', handleItemClick);
        // Add the click handler
        item.addEventListener('click', handleItemClick);
    });
}

/**
 * Generic function to handle list item click events
 * @param {Event} event - The click event
 */
function handleItemClick(event) {
    console.log('List item clicked');
    // Prevent any default behavior
    event.preventDefault();
    
    // Get the item ID from the data attribute
    const itemId = this.getAttribute('data-id');
    if (!itemId) {
        console.warn('No item ID found on clicked element');
        return;
    }
    
    console.log(`Loading details for item ID: ${itemId}`);
    
    // Mark this item as selected
    document.querySelectorAll('.list-item-card').forEach(item => {
        item.classList.remove('selected');
    });
    this.classList.add('selected');
    
    // Load the details - this will be handled by the appropriate page object
    if (window.currentPage) {
        console.log('Using currentPage object to fetch details:', window.currentPage);
        window.currentPage.fetchItemDetails(itemId);
    } else {
        console.warn('No currentPage object found to handle item click');
        
        // Try to find a page-specific handler based on the current URL
        const path = window.location.pathname;
        console.log('Current path:', path);
        
        if (path.includes('/molecules')) {
            console.log('Detected molecules page, trying to use moleculePage');
            if (window.moleculePage && typeof window.moleculePage.fetchItemDetails === 'function') {
                window.moleculePage.fetchItemDetails(itemId);
            } else if (typeof loadMoleculeDetails === 'function') {
                loadMoleculeDetails(itemId);
            } else {
                console.error('No molecule handler functions found');
            }
        } else if (path.includes('/targets')) {
            console.log('Detected targets page, trying to use targetPage');
            if (window.targetPage && typeof window.targetPage.fetchItemDetails === 'function') {
                window.targetPage.fetchItemDetails(itemId);
            } else if (typeof loadTargetDetails === 'function') {
                loadTargetDetails(itemId);
            } else {
                console.error('No target handler functions found');
            }
        } else if (path.includes('/organisms')) {
            console.log('Detected organisms page, trying to use organismPage');
            if (window.organismPage && typeof window.organismPage.fetchItemDetails === 'function') {
                window.organismPage.fetchItemDetails(itemId);
            } else if (typeof loadOrganismDetails === 'function') {
                loadOrganismDetails(itemId);
            } else {
                console.error('No organism handler functions found');
            }
        } else if (path.includes('/effects')) {
            console.log('Detected effects page, trying to use effectPage');
            if (window.effectPage && typeof window.effectPage.fetchItemDetails === 'function') {
                window.effectPage.fetchItemDetails(itemId);
            } else if (typeof loadEffectDetails === 'function') {
                loadEffectDetails(itemId);
            } else {
                console.error('No effect handler functions found');
            }
        } else {
            console.error('Unknown page type:', path);
        }
    }
}

/**
 * Set up mutation observer to automatically attach event listeners when new list items are added
 */
function setupListItemObserver() {
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                // Check if any list items were added
                const hasListItems = Array.from(mutation.addedNodes).some(node => 
                    node.nodeType === 1 && 
                    ((node.classList && node.classList.contains('list-item-card')) ||
                     (node.querySelector && node.querySelector('.list-item-card')))
                );
                
                if (hasListItems) {
                    // Re-attach event listeners
                    attachListItemEventListeners();
                }
            }
        });
    });
    
    // Observe the items list container for changes
    const itemsList = document.getElementById('itemsList');
    if (itemsList) {
        observer.observe(itemsList, { childList: true, subtree: true });
        console.log('Observing items list for changes');
    }
}

// Initialize when the document is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('list_utils.js: Document loaded, initializing list handlers');
    
    // Make sure list event handlers are attached when the list is loaded
    attachListItemEventListeners();
    
    // Set up observer for dynamic changes
    setupListItemObserver();
});

// Export functions for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        attachListItemEventListeners,
        handleItemClick,
        setupListItemObserver
    };
} 