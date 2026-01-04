/**
 * PBX Control Portal - Admin Panel JavaScript
 * Handles all UI interactions and API communication
 */

// API Configuration
const API_BASE_URL = window.location.origin;

// Global state
let allUsers = [];
let currentSort = { column: 'created', direction: 'desc' };
let deleteUserId = null;

// Bootstrap modal instances
let addUserModal, deleteModal, applyModal;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap modals
    addUserModal = new bootstrap.Modal(document.getElementById('addUserModal'));
    deleteModal = new bootstrap.Modal(document.getElementById('deleteModal'));
    applyModal = new bootstrap.Modal(document.getElementById('applyModal'));

    // Load initial data
    refreshUsers();
    loadApplyHistory();
});

// ============================================================================
// API Functions
// ============================================================================

/**
 * Fetch all users from API
 */
async function fetchUsers() {
    try {
        const response = await fetch(`${API_BASE_URL}/users`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching users:', error);
        showToast('Error', 'Failed to load users', 'error');
        throw error;
    }
}

/**
 * Create a new user
 */
async function createUserAPI(name, email) {
    try {
        const response = await fetch(`${API_BASE_URL}/users`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name, email })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to create user');
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error creating user:', error);
        throw error;
    }
}

/**
 * Delete a user by ID
 */
async function deleteUserAPI(userId) {
    try {
        const response = await fetch(`${API_BASE_URL}/users/${userId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to delete user');
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error deleting user:', error);
        throw error;
    }
}

/**
 * Apply configuration to Asterisk
 */
async function applyConfigurationAPI() {
    try {
        const response = await fetch(`${API_BASE_URL}/apply`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ triggered_by: 'Administrator' })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to apply configuration');
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error applying configuration:', error);
        throw error;
    }
}

/**
 * Get apply history/audit logs
 */
async function getApplyHistory() {
    try {
        const response = await fetch(`${API_BASE_URL}/apply/history`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching apply history:', error);
        return [];
    }
}

// ============================================================================
// User Management Functions
// ============================================================================

/**
 * Refresh users table
 */
async function refreshUsers() {
    try {
        showLoadingRow();
        allUsers = await fetchUsers();
        renderUsersTable(allUsers);
        updateStatistics(allUsers);
    } catch (error) {
        showEmptyState('Failed to load users. Please try again.');
    }
}

/**
 * Show loading row in table
 */
function showLoadingRow() {
    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = `
        <tr id="loadingRow">
            <td colspan="5" class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2 text-muted">Loading users...</p>
            </td>
        </tr>
    `;
}

/**
 * Show empty state in table
 */
function showEmptyState(message = 'No users found') {
    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = `
        <tr>
            <td colspan="5" class="empty-state">
                <i class="fas fa-users"></i>
                <p>${message}</p>
            </td>
        </tr>
    `;
    document.getElementById('userCount').textContent = 'Showing 0 users';
}

/**
 * Render users table
 */
function renderUsersTable(users) {
    const tbody = document.getElementById('usersTableBody');

    if (!users || users.length === 0) {
        showEmptyState();
        return;
    }

    tbody.innerHTML = users.map(user => {
        const extension = user.extension || {};
        const extensionNumber = extension.number || 'N/A';
        const secret = extension.secret || 'N/A';
        const createdDate = new Date(user.created_at).toLocaleString();

        return `
            <tr>
                <td><strong>${escapeHtml(user.name)}</strong></td>
                <td>${escapeHtml(user.email)}</td>
                <td>
                    <span class="extension-number">${extensionNumber}</span>
                </td>
                <td>
                    <small class="text-muted">${createdDate}</small>
                </td>
                <td class="text-end">
                    <button class="btn btn-sm btn-outline-secondary btn-action"
                            onclick="copySecret('${secret}')"
                            title="Copy SIP Secret">
                        <i class="fas fa-key"></i>
                    </button>
                    <button class="btn btn-sm btn-danger btn-action"
                            onclick="showDeleteModal('${user.id}', '${escapeHtml(user.name)}', '${escapeHtml(user.email)}', '${extensionNumber}')"
                            title="Delete User">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    document.getElementById('userCount').textContent = `Showing ${users.length} users`;
}

/**
 * Filter users based on search input
 */
function filterUsers() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();

    if (!searchTerm) {
        renderUsersTable(allUsers);
        return;
    }

    const filtered = allUsers.filter(user => {
        const name = (user.name || '').toLowerCase();
        const email = (user.email || '').toLowerCase();
        const extension = (user.extension?.number || '').toString();

        return name.includes(searchTerm) ||
               email.includes(searchTerm) ||
               extension.includes(searchTerm);
    });

    renderUsersTable(filtered);
}

/**
 * Sort table by column
 */
function sortTable(column) {
    // Toggle direction if same column
    if (currentSort.column === column) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.column = column;
        currentSort.direction = 'asc';
    }

    // Sort users array
    const sorted = [...allUsers].sort((a, b) => {
        let aVal, bVal;

        switch (column) {
            case 'name':
                aVal = a.name.toLowerCase();
                bVal = b.name.toLowerCase();
                break;
            case 'email':
                aVal = a.email.toLowerCase();
                bVal = b.email.toLowerCase();
                break;
            case 'extension':
                aVal = a.extension?.number || 0;
                bVal = b.extension?.number || 0;
                break;
            case 'created':
                aVal = new Date(a.created_at).getTime();
                bVal = new Date(b.created_at).getTime();
                break;
            default:
                return 0;
        }

        if (aVal < bVal) return currentSort.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return currentSort.direction === 'asc' ? 1 : -1;
        return 0;
    });

    renderUsersTable(sorted);
}

/**
 * Update statistics cards
 */
function updateStatistics(users) {
    // Total users
    document.getElementById('totalUsers').textContent = users.length;

    // Available extensions (1000-1999 range = 1000 extensions)
    const usedExtensions = users.filter(u => u.extension).length;
    const availableExtensions = 1000 - usedExtensions;
    document.getElementById('availableExtensions').textContent = availableExtensions;

    // Created today
    const today = new Date().toDateString();
    const createdToday = users.filter(u => {
        const createdDate = new Date(u.created_at).toDateString();
        return createdDate === today;
    }).length;
    document.getElementById('extensionsToday').textContent = createdToday;
}

// ============================================================================
// Modal Functions
// ============================================================================

/**
 * Show Add User modal
 */
function showAddUserModal() {
    // Reset form
    document.getElementById('addUserForm').reset();
    document.getElementById('addUserError').classList.add('d-none');
    addUserModal.show();
}

/**
 * Create user from form
 */
async function createUser(event) {
    event.preventDefault();

    const name = document.getElementById('userName').value.trim();
    const email = document.getElementById('userEmail').value.trim();
    const errorDiv = document.getElementById('addUserError');

    if (!name || !email) {
        errorDiv.textContent = 'Please fill in all required fields';
        errorDiv.classList.remove('d-none');
        return;
    }

    // Get submit button (it's outside the form)
    const submitBtn = document.querySelector('button[form="addUserForm"]');

    try {
        // Disable submit button
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Creating...';
        }

        const result = await createUserAPI(name, email);

        // Close modal
        addUserModal.hide();

        // Show success message
        showToast('Success', `User created with extension ${result.extension.number}`, 'success');

        // Refresh table
        await refreshUsers();

    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('d-none');
    } finally {
        // Re-enable submit button
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-plus me-1"></i> Create User';
        }
    }
}

/**
 * Show Delete confirmation modal
 */
function showDeleteModal(userId, userName, userEmail, extension) {
    deleteUserId = userId;
    document.getElementById('deleteUserName').textContent = userName;
    document.getElementById('deleteUserEmail').textContent = userEmail;
    document.getElementById('deleteUserExtension').textContent = extension;
    deleteModal.show();
}

/**
 * Confirm user deletion
 */
async function confirmDelete() {
    if (!deleteUserId) return;

    try {
        const result = await deleteUserAPI(deleteUserId);

        // Close modal
        deleteModal.hide();

        // Show success message
        showToast('Deleted', `Extension ${result.freed_extension} has been freed`, 'success');

        // Refresh table
        await refreshUsers();

    } catch (error) {
        showToast('Error', error.message, 'error');
    } finally {
        deleteUserId = null;
    }
}

/**
 * Show Apply Configuration modal
 */
async function showApplyModal() {
    const modalBody = document.getElementById('applyModalBody');
    const modalFooter = document.getElementById('applyModalFooter');

    // Show confirmation UI
    modalBody.innerHTML = `
        <div class="alert alert-warning">
            <i class="fas fa-exclamation-triangle me-2"></i>
            This will generate new Asterisk configuration files and reload the PBX.
        </div>
        <p><strong>Current Users:</strong> ${allUsers.length}</p>
        <p><strong>Extensions to Configure:</strong> ${allUsers.filter(u => u.extension).length}</p>
        <p class="mb-0">Do you want to proceed?</p>
    `;

    modalFooter.innerHTML = `
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
        <button type="button" class="btn btn-warning" onclick="executeApply()">
            <i class="fas fa-bolt me-1"></i> Apply Now
        </button>
    `;

    applyModal.show();
}

/**
 * Execute apply operation
 */
async function executeApply() {
    const modalBody = document.getElementById('applyModalBody');
    const modalFooter = document.getElementById('applyModalFooter');
    const closeBtn = document.getElementById('applyCloseBtn');

    // Disable close button during operation
    closeBtn.disabled = true;

    // Show progress UI
    modalBody.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-warning mb-3" role="status">
                <span class="visually-hidden">Applying...</span>
            </div>
            <h5>Applying Configuration...</h5>
            <p class="text-muted">Please wait while the configuration is applied to Asterisk.</p>
            <div class="progress mt-3">
                <div class="progress-bar progress-bar-striped progress-bar-animated"
                     role="progressbar" style="width: 100%"></div>
            </div>
        </div>
    `;

    modalFooter.innerHTML = '';

    try {
        const result = await applyConfigurationAPI();

        // Show success UI
        modalBody.innerHTML = `
            <div class="alert alert-success">
                <i class="fas fa-check-circle me-2"></i>
                Configuration applied successfully!
            </div>
            <div class="row">
                <div class="col-6">
                    <p class="mb-1"><strong>Users Applied:</strong></p>
                    <p class="text-muted">${result.users_applied}</p>
                </div>
                <div class="col-6">
                    <p class="mb-1"><strong>Extensions Generated:</strong></p>
                    <p class="text-muted">${result.extensions_generated}</p>
                </div>
            </div>
            <details class="mt-3">
                <summary class="cursor-pointer"><strong>Reload Results</strong></summary>
                <pre class="mt-2 p-2 bg-light rounded"><code>${JSON.stringify(result.reload_results, null, 2)}</code></pre>
            </details>
        `;

        modalFooter.innerHTML = `
            <button type="button" class="btn btn-success" data-bs-dismiss="modal">
                <i class="fas fa-check me-1"></i> Done
            </button>
        `;

        // Update statistics
        updateLastApplyStatus('success');

        // Reload history
        await loadApplyHistory();

        showToast('Success', 'Configuration applied to Asterisk', 'success');

    } catch (error) {
        // Show error UI
        modalBody.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-circle me-2"></i>
                <strong>Apply Failed</strong>
            </div>
            <p class="text-danger">${error.message}</p>
            <p class="text-muted">Please check the logs and try again.</p>
        `;

        modalFooter.innerHTML = `
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
            <button type="button" class="btn btn-warning" onclick="executeApply()">
                <i class="fas fa-redo me-1"></i> Retry
            </button>
        `;

        updateLastApplyStatus('failure');
        showToast('Error', 'Failed to apply configuration', 'error');
    } finally {
        // Re-enable close button
        closeBtn.disabled = false;
    }
}

/**
 * Update last apply status card
 */
function updateLastApplyStatus(status) {
    const statusElement = document.getElementById('lastApplyStatus');
    const iconElement = document.getElementById('lastApplyIcon');
    const now = new Date().toLocaleString();

    if (status === 'success') {
        statusElement.textContent = now;
        iconElement.className = 'fas fa-check-circle fa-2x text-success mb-2';
    } else {
        statusElement.textContent = 'Failed';
        iconElement.className = 'fas fa-exclamation-circle fa-2x text-danger mb-2';
    }
}

// ============================================================================
// Apply History Functions
// ============================================================================

/**
 * Load and render apply history
 */
async function loadApplyHistory() {
    const historyContainer = document.getElementById('applyHistory');

    try {
        const history = await getApplyHistory();

        if (!history || history.length === 0) {
            historyContainer.innerHTML = '<p class="text-muted mb-0">No configuration changes yet.</p>';
            return;
        }

        // Take last 5 entries
        const recentHistory = history.slice(0, 5);

        historyContainer.innerHTML = recentHistory.map(entry => {
            const timestamp = new Date(entry.triggered_at).toLocaleString();
            const outcomeClass = entry.outcome === 'success' ? 'success' : 'failure';
            const icon = entry.outcome === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';
            const badgeClass = entry.outcome === 'success' ? 'bg-success' : 'bg-danger';

            return `
                <div class="apply-history-item ${outcomeClass}">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <i class="fas ${icon} me-2"></i>
                            <strong>${entry.triggered_by}</strong>
                            <span class="badge ${badgeClass} ms-2">${entry.outcome}</span>
                        </div>
                        <small class="text-muted">${timestamp}</small>
                    </div>
                    ${entry.error_details ? `<p class="text-danger mb-0 mt-1 ms-4"><small>${entry.error_details}</small></p>` : ''}
                </div>
            `;
        }).join('');

        // Update last apply status card
        if (recentHistory.length > 0) {
            const latest = recentHistory[0];
            updateLastApplyStatus(latest.outcome);
        }

    } catch (error) {
        historyContainer.innerHTML = '<p class="text-muted mb-0">Failed to load history.</p>';
    }
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Copy SIP secret to clipboard
 */
async function copySecret(secret) {
    try {
        await navigator.clipboard.writeText(secret);
        showToast('Copied', 'SIP secret copied to clipboard', 'info');
    } catch (error) {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = secret;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showToast('Copied', 'SIP secret copied to clipboard', 'info');
    }
}

/**
 * Show toast notification
 */
function showToast(title, message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastIcon = document.getElementById('toastIcon');
    const toastTitle = document.getElementById('toastTitle');
    const toastBody = document.getElementById('toastBody');

    // Set icon based on type
    const icons = {
        'success': 'fa-check-circle text-success',
        'error': 'fa-exclamation-circle text-danger',
        'warning': 'fa-exclamation-triangle text-warning',
        'info': 'fa-info-circle text-info'
    };

    toastIcon.className = `fas ${icons[type] || icons.info} me-2`;
    toastTitle.textContent = title;
    toastBody.textContent = message;

    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
