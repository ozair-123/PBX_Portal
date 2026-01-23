/**
 * PBX Control Portal - DID Management JavaScript
 * Handles all DID-related UI interactions and API communication
 */

// Global state for DIDs
let allDIDs = [];
let allTenants = [];
let didModals = {
    import: null,
    allocate: null,
    assign: null
};

// Initialize DID modals on page load
document.addEventListener('DOMContentLoaded', function() {
    didModals.import = new bootstrap.Modal(document.getElementById('importDIDsModal'));
    didModals.allocate = new bootstrap.Modal(document.getElementById('allocateDIDModal'));
    didModals.assign = new bootstrap.Modal(document.getElementById('assignDIDModal'));
});

// ============================================================================
// Tab Switching
// ============================================================================

/**
 * Switch between Users and DIDs tabs
 */
function switchTab(tab) {
    if (tab === 'dids') {
        // Load DIDs when switching to DIDs tab
        refreshDIDs();
        loadTenants(); // Preload tenants for allocate modal
    }
}

// ============================================================================
// API Functions - DIDs
// ============================================================================

/**
 * Fetch all DIDs from API
 */
async function fetchDIDs() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/dids`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return data.phone_numbers || [];
    } catch (error) {
        console.error('Error fetching DIDs:', error);
        showToast('Error', 'Failed to load phone numbers', 'error');
        throw error;
    }
}

/**
 * Import DIDs
 */
async function importDIDsAPI(didsData) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/dids/import`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ dids: didsData })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to import DIDs');
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error importing DIDs:', error);
        throw error;
    }
}

/**
 * Allocate DID to tenant
 */
async function allocateDIDAPI(phoneNumberId, tenantId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/dids/${phoneNumberId}/allocate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ tenant_id: tenantId })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to allocate DID');
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error allocating DID:', error);
        throw error;
    }
}

/**
 * Assign DID to destination
 */
async function assignDIDAPI(phoneNumberId, assignedType, assignedId, assignedValue) {
    try {
        const payload = {
            assigned_type: assignedType,
            assigned_id: assignedId,
            assigned_value: assignedValue
        };

        const response = await fetch(`${API_BASE_URL}/api/v1/dids/${phoneNumberId}/assign`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to assign DID');
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error assigning DID:', error);
        throw error;
    }
}

/**
 * Unassign DID
 */
async function unassignDIDAPI(phoneNumberId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/dids/${phoneNumberId}/assign`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to unassign DID');
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error unassigning DID:', error);
        throw error;
    }
}

/**
 * Fetch tenants
 */
async function fetchTenants() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/tenants`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return data.tenants || [];
    } catch (error) {
        console.error('Error fetching tenants:', error);
        return [];
    }
}

// ============================================================================
// DID Management Functions
// ============================================================================

/**
 * Refresh DIDs table
 */
async function refreshDIDs() {
    try {
        showLoadingDIDsRow();
        allDIDs = await fetchDIDs();
        renderDIDsTable(allDIDs);
        updateDIDStatistics(allDIDs);
    } catch (error) {
        showEmptyDIDsState('Failed to load phone numbers. Please try again.');
    }
}

/**
 * Show loading row in DIDs table
 */
function showLoadingDIDsRow() {
    const tbody = document.getElementById('didsTableBody');
    tbody.innerHTML = `
        <tr id="loadingDIDsRow">
            <td colspan="6" class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2 text-muted">Loading phone numbers...</p>
            </td>
        </tr>
    `;
}

/**
 * Show empty state in DIDs table
 */
function showEmptyDIDsState(message = 'No phone numbers found') {
    const tbody = document.getElementById('didsTableBody');
    tbody.innerHTML = `
        <tr>
            <td colspan="6" class="empty-state">
                <i class="fas fa-phone"></i>
                <p>${message}</p>
            </td>
        </tr>
    `;
    document.getElementById('didCount').textContent = 'Showing 0 phone numbers';
}

/**
 * Render DIDs table
 */
function renderDIDsTable(dids) {
    const tbody = document.getElementById('didsTableBody');

    if (!dids || dids.length === 0) {
        showEmptyDIDsState();
        return;
    }

    tbody.innerHTML = dids.map(did => {
        const statusBadge = getStatusBadge(did.status);
        const tenantName = did.tenant_name || '-';
        const assignedTo = getAssignedToDisplay(did);
        const provider = did.provider || '-';
        const actions = getActionButtons(did);

        return `
            <tr>
                <td><strong class="font-monospace">${escapeHtml(did.number)}</strong></td>
                <td>${statusBadge}</td>
                <td>${escapeHtml(tenantName)}</td>
                <td>${assignedTo}</td>
                <td>${escapeHtml(provider)}</td>
                <td class="text-end">${actions}</td>
            </tr>
        `;
    }).join('');

    document.getElementById('didCount').textContent = `Showing ${dids.length} phone numbers`;
}

/**
 * Get status badge HTML
 */
function getStatusBadge(status) {
    const badges = {
        'UNASSIGNED': '<span class="badge bg-secondary">UNASSIGNED</span>',
        'ALLOCATED': '<span class="badge bg-info">ALLOCATED</span>',
        'ASSIGNED': '<span class="badge bg-success">ASSIGNED</span>'
    };
    return badges[status] || `<span class="badge bg-secondary">${status}</span>`;
}

/**
 * Get assigned to display text
 */
function getAssignedToDisplay(did) {
    if (did.status !== 'ASSIGNED') return '-';

    if (did.assigned_type === 'USER' && did.assigned_user_name) {
        return `<i class="fas fa-user me-1"></i>${escapeHtml(did.assigned_user_name)} (${did.assigned_extension})`;
    } else if (did.assigned_type === 'EXTERNAL') {
        return `<i class="fas fa-code me-1"></i>External`;
    } else {
        return did.assigned_type;
    }
}

/**
 * Get action buttons based on DID status
 */
function getActionButtons(did) {
    const buttons = [];

    if (did.status === 'UNASSIGNED') {
        buttons.push(`
            <button class="btn btn-sm btn-primary btn-action"
                    onclick='showAllocateDIDModal(${JSON.stringify(did)})'
                    title="Allocate to Tenant">
                <i class="fas fa-building"></i>
            </button>
        `);
    }

    if (did.status === 'ALLOCATED') {
        buttons.push(`
            <button class="btn btn-sm btn-success btn-action"
                    onclick='showAssignDIDModal(${JSON.stringify(did)})'
                    title="Assign to Destination">
                <i class="fas fa-user-tag"></i>
            </button>
        `);
    }

    if (did.status === 'ASSIGNED') {
        buttons.push(`
            <button class="btn btn-sm btn-warning btn-action"
                    onclick='unassignDIDConfirm("${did.id}", "${escapeHtml(did.number)}")'
                    title="Unassign">
                <i class="fas fa-undo"></i>
            </button>
        `);
    }

    return buttons.join(' ');
}

/**
 * Filter DIDs based on search input
 */
function filterDIDs() {
    const searchTerm = document.getElementById('searchDIDsInput').value.toLowerCase();

    if (!searchTerm) {
        renderDIDsTable(allDIDs);
        return;
    }

    const filtered = allDIDs.filter(did => {
        const number = (did.number || '').toLowerCase();
        const provider = (did.provider || '').toLowerCase();
        const tenant = (did.tenant_name || '').toLowerCase();

        return number.includes(searchTerm) ||
               provider.includes(searchTerm) ||
               tenant.includes(searchTerm);
    });

    renderDIDsTable(filtered);
}

/**
 * Update DID statistics cards
 */
function updateDIDStatistics(dids) {
    const total = dids.length;
    const assigned = dids.filter(d => d.status === 'ASSIGNED').length;
    const allocated = dids.filter(d => d.status === 'ALLOCATED').length;
    const unassigned = dids.filter(d => d.status === 'UNASSIGNED').length;

    document.getElementById('totalDIDs').textContent = total;
    document.getElementById('assignedDIDs').textContent = assigned;
    document.getElementById('allocatedDIDs').textContent = allocated;
    document.getElementById('unassignedDIDs').textContent = unassigned;
}

// ============================================================================
// Modal Functions - Import DIDs
// ============================================================================

/**
 * Show Import DIDs modal
 */
function showImportDIDsModal() {
    document.getElementById('importDIDsForm').reset();
    document.getElementById('importDIDsError').classList.add('d-none');
    didModals.import.show();
}

/**
 * Import DIDs from form
 */
async function importDIDs(event) {
    event.preventDefault();

    const textarea = document.getElementById('didsTextarea').value.trim();
    const errorDiv = document.getElementById('importDIDsError');

    if (!textarea) {
        errorDiv.textContent = 'Please enter at least one phone number';
        errorDiv.classList.remove('d-none');
        return;
    }

    // Parse textarea input
    const lines = textarea.split('\n').filter(line => line.trim());
    const didsData = [];

    for (const line of lines) {
        const parts = line.split(',').map(p => p.trim());
        if (parts.length < 1) continue;

        const didItem = {
            number: parts[0],
            provider: parts[1] || null,
            provider_metadata: {}
        };

        // Try to parse JSON metadata if provided
        if (parts[2]) {
            try {
                didItem.provider_metadata = JSON.parse(parts[2]);
            } catch (e) {
                // Ignore JSON parse errors
            }
        }

        didsData.push(didItem);
    }

    const submitBtn = document.querySelector('button[form="importDIDsForm"]');

    try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Importing...';

        const result = await importDIDsAPI(didsData);

        didModals.import.hide();

        if (result.failed > 0) {
            const errorDetails = result.errors.map(e => `${e.number}: ${e.error}`).join(', ');
            showToast('Partial Import', `Imported ${result.imported}, failed ${result.failed}`, 'warning');
        } else {
            showToast('Success', `Imported ${result.imported} phone numbers`, 'success');
        }

        await refreshDIDs();

    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('d-none');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-upload me-1"></i> Import DIDs';
    }
}

// ============================================================================
// Modal Functions - Allocate DID
// ============================================================================

/**
 * Load tenants for allocate modal
 */
async function loadTenants() {
    if (allTenants.length > 0) return; // Already loaded

    allTenants = await fetchTenants();

    const select = document.getElementById('allocateTenantId');
    if (allTenants.length === 0) {
        select.innerHTML = '<option value="">No tenants available</option>';
    } else {
        select.innerHTML = '<option value="">Select tenant...</option>' +
            allTenants.map(t => `<option value="${t.id}">${escapeHtml(t.name)}</option>`).join('');
    }
}

/**
 * Show Allocate DID modal
 */
async function showAllocateDIDModal(did) {
    document.getElementById('allocateDIDForm').reset();
    document.getElementById('allocateDIDError').classList.add('d-none');
    document.getElementById('allocatePhoneNumberId').value = did.id;
    document.getElementById('allocatePhoneNumber').value = did.number;

    await loadTenants();
    didModals.allocate.show();
}

/**
 * Allocate DID from form
 */
async function allocateDID(event) {
    event.preventDefault();

    const phoneNumberId = document.getElementById('allocatePhoneNumberId').value;
    const tenantId = document.getElementById('allocateTenantId').value;
    const errorDiv = document.getElementById('allocateDIDError');

    if (!tenantId) {
        errorDiv.textContent = 'Please select a tenant';
        errorDiv.classList.remove('d-none');
        return;
    }

    const submitBtn = document.querySelector('button[form="allocateDIDForm"]');

    try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Allocating...';

        await allocateDIDAPI(phoneNumberId, tenantId);

        didModals.allocate.hide();
        showToast('Success', 'DID allocated to tenant', 'success');
        await refreshDIDs();

    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('d-none');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-check me-1"></i> Allocate to Tenant';
    }
}

// ============================================================================
// Modal Functions - Assign DID
// ============================================================================

/**
 * Show Assign DID modal
 */
async function showAssignDIDModal(did) {
    document.getElementById('assignDIDForm').reset();
    document.getElementById('assignDIDError').classList.add('d-none');
    document.getElementById('assignPhoneNumberId').value = did.id;
    document.getElementById('assignPhoneNumber').value = did.number;

    // Hide all conditional fields
    document.getElementById('userSelectGroup').style.display = 'none';
    document.getElementById('externalValueGroup').style.display = 'none';

    // Load users for this tenant
    await loadUsersForAssignment(did.tenant_id);

    didModals.assign.show();
}

/**
 * Load users for assignment modal
 */
async function loadUsersForAssignment(tenantId) {
    const select = document.getElementById('assignedUserId');

    try {
        const users = await fetchUsers(); // Reuse existing function
        const tenantUsers = users.filter(u => u.tenant_id === tenantId);

        if (tenantUsers.length === 0) {
            select.innerHTML = '<option value="">No users available in this tenant</option>';
        } else {
            select.innerHTML = '<option value="">Select user...</option>' +
                tenantUsers.map(u => {
                    const ext = u.extension?.number || 'No ext';
                    return `<option value="${u.id}">${escapeHtml(u.name)} (${ext})</option>`;
                }).join('');
        }
    } catch (error) {
        select.innerHTML = '<option value="">Error loading users</option>';
    }
}

/**
 * Update assignment fields based on type
 */
function updateAssignmentFields() {
    const type = document.getElementById('assignedType').value;
    const userGroup = document.getElementById('userSelectGroup');
    const externalGroup = document.getElementById('externalValueGroup');

    // Hide all
    userGroup.style.display = 'none';
    externalGroup.style.display = 'none';

    // Show relevant field
    if (type === 'USER') {
        userGroup.style.display = 'block';
        document.getElementById('assignedUserId').required = true;
        document.getElementById('assignedValue').required = false;
    } else if (type === 'EXTERNAL') {
        externalGroup.style.display = 'block';
        document.getElementById('assignedValue').required = true;
        document.getElementById('assignedUserId').required = false;
    }
}

/**
 * Assign DID from form
 */
async function assignDID(event) {
    event.preventDefault();

    const phoneNumberId = document.getElementById('assignPhoneNumberId').value;
    const assignedType = document.getElementById('assignedType').value;
    const errorDiv = document.getElementById('assignDIDError');

    let assignedId = null;
    let assignedValue = null;

    if (assignedType === 'USER') {
        assignedId = document.getElementById('assignedUserId').value;
        if (!assignedId) {
            errorDiv.textContent = 'Please select a user';
            errorDiv.classList.remove('d-none');
            return;
        }
    } else if (assignedType === 'EXTERNAL') {
        assignedValue = document.getElementById('assignedValue').value.trim();
        if (!assignedValue) {
            errorDiv.textContent = 'Please enter dialplan context';
            errorDiv.classList.remove('d-none');
            return;
        }
    }

    const submitBtn = document.querySelector('button[form="assignDIDForm"]');

    try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Assigning...';

        await assignDIDAPI(phoneNumberId, assignedType, assignedId, assignedValue);

        didModals.assign.hide();
        showToast('Success', 'DID assigned to destination', 'success');
        await refreshDIDs();

    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('d-none');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-check me-1"></i> Assign DID';
    }
}

/**
 * Unassign DID confirmation
 */
async function unassignDIDConfirm(phoneNumberId, phoneNumber) {
    if (!confirm(`Unassign ${phoneNumber}?\n\nThis will change status from ASSIGNED → ALLOCATED`)) {
        return;
    }

    try {
        await unassignDIDAPI(phoneNumberId);
        showToast('Success', `${phoneNumber} unassigned`, 'success');
        await refreshDIDs();
    } catch (error) {
        showToast('Error', error.message, 'error');
    }
}
