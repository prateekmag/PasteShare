/**
 * PetrolPro - Main JavaScript File
 * Contains shared functions for the PetrolPro web application.
 */

// Ensure branch dropdown is always populated after DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (typeof loadBranches === 'function') {
        loadBranches();
    } else {
        console.error('loadBranches function not found!');
    }
    
    // Listen for branchDataUpdated to re-populate the dropdown (for SPA/analytics page)
    window.addEventListener('branchDataUpdated', function() {
        const branchSelector = document.getElementById('branch-selector');
        if (branchSelector) {
            const branches = JSON.parse(localStorage.getItem('branchData')) || [];
            branchSelector.length = 1; // keep "Select Branch" option
            branches.forEach(b => {
                if (b && (b.id || b.name)) {
                    const option = document.createElement('option');
                    option.value = b.id || b._id || b.branch_id;
                    option.textContent = b.name || b.branch_name;
                    branchSelector.appendChild(option);
                }
            });
        }
    });
});

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - The type of alert (success, danger, warning, info)
 */
function showAlert(message, type = 'info') {
    const alertsContainer = document.createElement('div');
    alertsContainer.className = 'position-fixed top-0 end-0 p-3';
    alertsContainer.style.zIndex = '1050';
    
    const alertHtml = `
        <div class="toast show" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <strong class="me-auto">PetrolPro</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body bg-${type} text-white">
                ${message}
            </div>
        </div>
    `;
    
    alertsContainer.innerHTML = alertHtml;
    document.body.appendChild(alertsContainer);
    
    // Remove the alert after 5 seconds
    setTimeout(() => {
        alertsContainer.remove();
    }, 5000);
}

/**
 * Format a date for input fields
 * @param {Date} date - The date to format
 * @returns {string} Formatted date string (YYYY-MM-DD)
 */
function formatDateForInput(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

/**
 * Format currency value
 * @param {number} value - The value to format
 * @returns {string} Formatted currency string
 */
function formatCurrency(value) {
    return '\u20B9' + parseFloat(value).toFixed(2);
}

/**
 * Format number with commas
 * @param {number} number - The number to format
 * @returns {string} Formatted number string
 */
function formatNumber(number) {
    return parseFloat(number).toLocaleString('en-US');
}

/**
 * Capitalize first letter of a string
 * @param {string} string - The string to capitalize
 * @returns {string} Capitalized string
 */
function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

/**
 * Format a date relative to now (e.g., "5 min ago")
 * @param {Date} date - The date to format
 * @returns {string} Formatted relative time
 */
function formatRelativeTime(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffMins < 60) {
        return diffMins + ' min ago';
    } else if (diffHours < 24) {
        return diffHours + ' hours ago';
    } else {
        return diffDays + ' days ago';
    }
}

/**
 * Get start and end dates for common periods
 * @param {string} period - The period (today, week, month, year)
 * @returns {Object} Object with start and end dates
 */
function getDateRange(period) {
    const now = new Date();
    let start, end;
    
    switch(period) {
        case 'today':
            start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
            end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
            break;
        case 'week':
            // Last 7 days
            start = new Date(now);
            start.setDate(start.getDate() - 7);
            end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
            break;
        case 'month':
            start = new Date(now.getFullYear(), now.getMonth(), 1);
            end = new Date(now.getFullYear(), now.getMonth() + 1, 0, 23, 59, 59);
            break;
        case 'year':
            start = new Date(now.getFullYear(), 0, 1);
            end = new Date(now.getFullYear(), 11, 31, 23, 59, 59);
            break;
        default:
            start = new Date(now.getFullYear(), now.getMonth(), 1);
            end = new Date(now.getFullYear(), now.getMonth() + 1, 0, 23, 59, 59);
    }
    
    return {
        start,
        end
    };
}

/**
 * Convert object to query string
 * @param {Object} params - The parameters object
 * @returns {string} Query string
 */
function objectToQueryString(params) {
    return Object.keys(params)
        .filter(key => params[key] !== undefined && params[key] !== null && params[key] !== '')
        .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
        .join('&');
}

/**
 * Create a color palette for charts
 * @param {number} count - Number of colors needed
 * @returns {Array} Array of colors
 */
function generateColorPalette(count) {
    const baseColors = [
        'rgba(75, 192, 192, 1)',
        'rgba(153, 102, 255, 1)',
        'rgba(255, 159, 64, 1)',
        'rgba(255, 99, 132, 1)',
        'rgba(54, 162, 235, 1)',
        'rgba(255, 205, 86, 1)'
    ];
    
    // If we need more colors than in the base set, generate them
    if (count <= baseColors.length) {
        return baseColors.slice(0, count);
    }
    
    const palette = [...baseColors];
    
    // Generate additional colors
    for (let i = baseColors.length; i < count; i++) {
        const hue = (i * 137) % 360; // Use golden ratio for good distribution
        palette.push(`hsla(${hue}, 70%, 60%, 1)`);
    }
    
    return palette;
}

/**
 * Generate translucent versions of colors for backgrounds
 * @param {Array} colors - Array of colors
 * @param {number} alpha - Alpha transparency (0-1)
 * @returns {Array} Array of translucent colors
 */
function getBackgroundColors(colors, alpha = 0.7) {
    return colors.map(color => {
        if (color.startsWith('rgb')) {
            return color.replace('rgb', 'rgba').replace(')', `, ${alpha})`);
        } else if (color.startsWith('hsl')) {
            return color.replace('hsl', 'hsla').replace(')', `, ${alpha})`);
        }
        return color;
    });
}

/**
 * Load branches dynamically and populate the branch selector dropdown
 * @param {boolean} forceReload - Whether to force reload by clearing localStorage
 */
function loadBranches(forceReload = false) {
    console.log("Loading branch list...");
    let branchSelector = document.getElementById('branch-selector');
    if (!branchSelector) {
        branchSelector = document.getElementById('branch-select');
    }
    // Always fetch and store branch data for analytics page
    fetch('/api/branch/branches?_=' + new Date().getTime(), {
        cache: 'no-store',
        headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    })
    .then(response => response.json())
    .then(branches => {
        console.log("Fetched branches:", branches);
        if (!Array.isArray(branches)) {
            console.error("Branch API did not return an array!", branches);
            showAlert('Branch API did not return a list. Check backend response.', 'danger');
            return;
        }
        // Filter out empty objects
        const filteredBranches = branches.filter(b => b && Object.keys(b).length > 0 && (b.id || b.name));
        if (filteredBranches.length === 0) {
            console.warn('Branch list is empty or contains only empty objects:', branches);
            showAlert('No valid branches found. Please check your backend data.', 'warning');
        }
        localStorage.setItem('branchData', JSON.stringify(filteredBranches));
        window.dispatchEvent(new Event('branchDataUpdated'));
        if (branchSelector) {
            branchSelector.length = 1; // keep the "Select Branch" option
            filteredBranches.forEach(branch => {
                const option = document.createElement('option');
                option.value = branch.id || branch._id || branch.branch_id;
                option.textContent = branch.name || branch.branch_name;
                branchSelector.appendChild(option);
            });
            console.log("Dropdown populated. Final options:", branchSelector.options);
        }
    })
    .catch(error => {
        console.error("Failed to fetch branches:", error);
    });
}

/**
 * Utility function to get a cookie by name
 * @param {string} name - The name of the cookie to retrieve
 * @returns {string|null} The cookie value or null if not found
 */
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

/**
 * Check if branches need to be refreshed from another page
 * This should be called on page load to detect branch updates from other tabs
 */
function checkBranchRefresh() {
    const shouldRefresh = getCookie('branch_refresh');
    if (shouldRefresh === 'true') {
        console.log("Branch refresh detected, reloading page");
        // Clear the cookie
        document.cookie = "branch_refresh=; path=/; max-age=0";
        // Clear localStorage
        localStorage.removeItem('selectedBranch');
        
        // Create a notification
        const refreshNotice = document.createElement('div');
        refreshNotice.className = 'alert alert-info alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-4';
        refreshNotice.style.zIndex = '9999';
        refreshNotice.innerHTML = `
            <strong>Branch data has changed!</strong> Refreshing page to show updated branch list...
        `;
        document.body.appendChild(refreshNotice);
        
        // Reload page after a short delay
        setTimeout(() => {
            window.location.reload(true);
        }, 1500);
        
        return true;
    }
    return false;
}

/**
 * Show a notification for empty data with information about deleted branches
 * @param {HTMLElement} container - The container element to append the message to
 * @param {string} entityName - The name of the entity type (e.g., "sales", "attendants")
 */
function showEmptyDataNotification(container, entityName) {
    const currentBranch = localStorage.getItem('selectedBranch');
    
    // Don't show special message for "all" branches
    if (currentBranch === 'all') {
        container.innerHTML = `<div class="alert alert-info">No ${entityName} records found.</div>`;
        return;
    }
    
    // Display a notification that suggests checking branch selection
    container.innerHTML = `
        <div class="alert alert-warning">
            <h5><i class="fas fa-exclamation-triangle me-2"></i> No ${entityName} records found</h5>
            <p>This could be because:</p>
            <ul>
                <li>There are no ${entityName} records for this branch</li>
                <li>The selected branch may have been deleted or modified</li>
            </ul>
            <p>Try switching to a different branch or to "All Branches" using the selector in the navigation bar.</p>
            <button class="btn btn-sm btn-primary refresh-branches-btn">Refresh Branch List</button>
        </div>
    `;
    
    // Add event listener to refresh branches button
    const refreshBtn = container.querySelector('.refresh-branches-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            loadBranches(true); // Force reload branches
            showAlert('Branch list refreshed. Please select a branch from the updated list.', 'success');
        });
    }
}

// Initialize event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Add null checks before adding event listeners
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }

    const registerForm = document.getElementById('registerForm'); 
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegistration);
    }

    const salesForm = document.getElementById('salesForm');
    if (salesForm) {
        salesForm.addEventListener('submit', handleSaleSubmission);
    }

    const fuelForm = document.getElementById('fuelForm');
    if (fuelForm) {
        fuelForm.addEventListener('submit', handleFuelEntry);
    }
});

/**
 * Check if a server response indicates a branch related error
 * @param {Object} data - The response data from the server
 * @returns {boolean} True if the error is branch-related
 */
function isBranchError(data) {
    if (!data) return false;
    
    // Check for typical error messages related to invalid branches
    if (data.status === 'error' && data.message) {
        const message = data.message.toLowerCase();
        return message.includes('branch') && 
              (message.includes('not found') || 
               message.includes('invalid') || 
               message.includes('deleted'));
    }
    
    return false;
}

/**
 * Handle branch errors by showing appropriate messages
 * @param {Object} error - The error object or response
 * @param {HTMLElement} container - The container element to show messages in
 * @param {string} entityName - The name of the entity type (e.g., "sales data")
 */
function handleBranchError(error, container, entityName) {
    console.error(`Error loading ${entityName}:`, error);
    
    if (container) {
        container.innerHTML = `
            <div class="alert alert-danger">
                <h5><i class="fas fa-exclamation-circle me-2"></i> Error Loading ${entityName}</h5>
                <p>There was a problem loading the ${entityName}. This may be because the selected branch no longer exists.</p>
                <p>Try switching to a different branch or to "All Branches" using the selector in the navigation bar.</p>
                <button class="btn btn-sm btn-primary refresh-branches-btn">Refresh Branch List</button>
            </div>
        `;
        
        // Add event listener to refresh branches button
        const refreshBtn = container.querySelector('.refresh-branches-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', function() {
                loadBranches(true); // Force reload branches
                showAlert('Branch list refreshed. Please select a branch from the updated list.', 'success');
            });
        }
    } else {
        // If no container is provided, just show an alert
        showAlert('Error loading data. The selected branch may no longer exist. Try refreshing the branch list.', 'danger');
    }
}