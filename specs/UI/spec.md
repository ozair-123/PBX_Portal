Frontend UI Specification - PBX Control Portal Admin Panel

  ---
  📋 1. OVERVIEW

  Purpose

  Web-based admin panel for non-technical users to manage PBX users, extensions, and Asterisk configuration without using command-line tools.

  Target Users

  - IT administrators (non-technical)
  - Office managers
  - Helpdesk staff
  - Anyone who needs to provision phone extensions

  Key Goals

  - ✅ Simple, intuitive interface (no technical knowledge required)
  - ✅ Visual feedback for all operations
  - ✅ Mobile-responsive (works on tablets/phones)
  - ✅ Real-time updates
  - ✅ Error handling with clear messages
  - ✅ Single-page application (no page refreshes)

  ---
  🎨 2. DESIGN PHILOSOPHY

  Visual Style

  - Clean & Modern: Minimalist design, lots of whitespace
  - Professional: Corporate blue/gray color scheme
  - Accessible: High contrast, large click targets
  - Familiar: Uses common UI patterns (tables, cards, modals)

  User Experience Principles

  1. Visibility: All important actions visible on main screen
  2. Feedback: Immediate visual confirmation for every action
  3. Safety: Confirmations for destructive actions (delete)
  4. Simplicity: Maximum 3 clicks to complete any task
  5. Forgiving: Easy undo/recovery from mistakes

  ---
  📐 3. PAGE LAYOUT

  Single Page Application (SPA)

  ┌─────────────────────────────────────────────────────────────────┐
  │  HEADER                                                          │
  │  ┌───────────────────────────────────────────────────────────┐  │
  │  │  🎙️ PBX Control Portal              👤 Admin  ⚙️ Settings │  │
  │  └───────────────────────────────────────────────────────────┘  │
  ├─────────────────────────────────────────────────────────────────┤
  │  ACTION BAR                                                      │
  │  ┌───────────────────────────────────────────────────────────┐  │
  │  │  [+ Add User]    [🔄 Refresh]    [⚡ Apply Configuration] │  │
  │  └───────────────────────────────────────────────────────────┘  │
  ├─────────────────────────────────────────────────────────────────┤
  │  STATISTICS CARDS (Row 1)                                        │
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
  │  │   42     │  │   958    │  │    3     │  │  Success │       │
  │  │  Users   │  │Available │  │Extensions│  │Last Apply│       │
  │  │          │  │Extensions│  │  Today   │  │  Status  │       │
  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
  ├─────────────────────────────────────────────────────────────────┤
  │  USERS TABLE (Main Content)                                     │
  │  ┌───────────────────────────────────────────────────────────┐  │
  │  │ Search: [_____________________] 🔍                         │  │
  │  │                                                            │  │
  │  │  Name ▲ │ Email          │ Extension │ Created   │ Actions│  │
  │  │─────────┼────────────────┼───────────┼───────────┼────────│  │
  │  │ John Doe│john@test.com   │   1000    │ 2 days ago│ 🗑️ 📋 │  │
  │  │ Jane S. │jane@test.com   │   1001    │ 2 days ago│ 🗑️ 📋 │  │
  │  │ Bob W.  │bob@test.com    │   1002    │ 1 day ago │ 🗑️ 📋 │  │
  │  │         │                │           │           │        │  │
  │  │  Showing 3 of 3 users                    Page 1 of 1     │  │
  │  └───────────────────────────────────────────────────────────┘  │
  ├─────────────────────────────────────────────────────────────────┤
  │  APPLY HISTORY (Bottom Section - Collapsible)                   │
  │  ┌───────────────────────────────────────────────────────────┐  │
  │  │  Recent Configuration Changes          [Show All ▼]       │  │
  │  │  ────────────────────────────────────────────────────────│  │
  │  │  ✅ Jan 4, 12:30 PM - Applied by admin@test.com          │  │
  │  │     2 users, 2 extensions generated                       │  │
  │  │  ✅ Jan 4, 12:15 PM - Applied by admin@test.com          │  │
  │  │     3 users, 3 extensions generated                       │  │
  │  └───────────────────────────────────────────────────────────┘  │
  └─────────────────────────────────────────────────────────────────┘

  ---
  🔧 4. FEATURES & COMPONENTS

  A. Header Bar

  - Logo: PBX Control Portal (with phone icon)
  - User Info: Display logged-in user (for future auth)
  - Settings: Future: Theme toggle, logout

  B. Action Bar

  1. "+ Add User" Button
    - Primary action, prominent blue button
    - Opens modal dialog
  2. "🔄 Refresh" Button
    - Reloads user list from server
    - Shows loading spinner during refresh
  3. "⚡ Apply Configuration" Button
    - Large, attention-grabbing (orange/red color)
    - Shows confirmation dialog
    - Displays progress during apply
    - Shows success/error message

  C. Statistics Dashboard

  Four Cards:

  1. Total Users
    - Count of active users
    - Icon: 👥
  2. Available Extensions
    - Calculation: 1000 - (current extension count)
    - Icon: 📞
  3. Extensions Created Today
    - Count of extensions created in last 24h
    - Icon: ➕
  4. Last Apply Status
    - Success/Failure with timestamp
    - Icon: ✅ or ❌

  D. Users Table

  Columns:
  1. Name (sortable)
  2. Email (sortable)
  3. Extension (sortable, filterable)
  4. Created Date (sortable, relative time: "2 days ago")
  5. Actions
    - 🗑️ Delete (red button, requires confirmation)
    - 📋 Copy Secret (copies SIP password to clipboard)

  Features:
  - Search/filter by name, email, or extension
  - Sortable columns (click header to sort)
  - Pagination (10/25/50/100 per page)
  - Hover effects on rows
  - Empty state: "No users yet. Click '+ Add User' to get started"

  Row Colors:
  - Default: White background
  - Hover: Light blue highlight
  - Selected: Blue highlight

  E. Add User Modal

  Triggered by: "+ Add User" button

  Layout:
  ┌─────────────────────────────────────┐
  │  Add New User                    [×]│
  ├─────────────────────────────────────┤
  │                                      │
  │  Full Name *                         │
  │  [_____________________________]     │
  │                                      │
  │  Email Address *                     │
  │  [_____________________________]     │
  │                                      │
  │  ℹ️ An extension (1000-1999) will   │
  │     be automatically assigned        │
  │                                      │
  │           [Cancel]  [Create User]    │
  └─────────────────────────────────────┘

  Validation:
  - Name: Required, 1-255 characters
  - Email: Required, valid email format, unique
  - Real-time validation (show errors as user types)
  - Disable "Create" button if form invalid

  On Success:
  - Close modal
  - Show toast notification: "✅ User created! Extension 1042 assigned"
  - Refresh user list
  - Highlight newly created user (fade-in animation)

  On Error:
  - Show error message in modal
  - Keep modal open
  - Highlight problematic field

  F. Delete Confirmation Modal

  ┌─────────────────────────────────────┐
  │  ⚠️  Confirm Delete              [×]│
  ├─────────────────────────────────────┤
  │                                      │
  │  Are you sure you want to delete:   │
  │                                      │
  │  👤 John Doe                         │
  │  📧 john@test.com                    │
  │  📞 Extension 1000                   │
  │                                      │
  │  This action cannot be undone.       │
  │  The extension will be freed for     │
  │  reuse.                              │
  │                                      │
  │           [Cancel]  [🗑️ Delete]     │
  └─────────────────────────────────────┘

  On Success:
  - Close modal
  - Show toast: "✅ User deleted. Extension 1000 is now available"
  - Remove row from table (fade-out animation)

  G. Apply Configuration Modal

  Triggered by: "⚡ Apply Configuration" button

  Step 1: Confirmation
  ┌─────────────────────────────────────┐
  │  ⚡ Apply Configuration          [×]│
  ├─────────────────────────────────────┤
  │                                      │
  │  This will:                          │
  │  ✓ Generate Asterisk configs for    │
  │    42 users (42 extensions)          │
  │  ✓ Write PJSIP endpoint configs      │
  │  ✓ Write dialplan routing            │
  │  ✓ Reload Asterisk modules           │
  │                                      │
  │  ⚠️ This may briefly interrupt       │
  │     active calls.                    │
  │                                      │
  │  Triggered by: admin@test.com        │
  │                                      │
  │           [Cancel]  [⚡ Apply Now]   │
  └─────────────────────────────────────┘

  Step 2: Progress
  ┌─────────────────────────────────────┐
  │  ⚡ Applying Configuration...        │
  ├─────────────────────────────────────┤
  │                                      │
  │  [████████░░░░░░░░░░] 60%            │
  │                                      │
  │  ✅ Generated PJSIP config           │
  │  ✅ Generated dialplan               │
  │  ⏳ Reloading Asterisk...            │
  │  ⏳ Creating audit log...            │
  │                                      │
  │  Please wait...                      │
  └─────────────────────────────────────┘

  Step 3: Success
  ┌─────────────────────────────────────┐
  │  ✅ Configuration Applied        [×]│
  ├─────────────────────────────────────┤
  │                                      │
  │  Success! Changes are live.          │
  │                                      │
  │  📄 Files written:                   │
  │  • generated_endpoints.conf          │
  │  • generated_routing.conf            │
  │                                      │
  │  🔄 Modules reloaded:                │
  │  • PJSIP ✅                          │
  │  • Dialplan ✅                       │
  │                                      │
  │  👥 42 users applied                 │
  │  📞 42 extensions generated          │
  │                                      │
  │              [Close]                 │
  └─────────────────────────────────────┘

  Step 3b: Error (if failure)
  ┌─────────────────────────────────────┐
  │  ❌ Configuration Failed         [×]│
  ├─────────────────────────────────────┤
  │                                      │
  │  Error applying configuration:       │
  │                                      │
  │  ⚠️ Asterisk reload failed           │
  │                                      │
  │  Details:                            │
  │  PJSIP module reload: Success ✅     │
  │  Dialplan reload: Failed ❌          │
  │                                      │
  │  Error: Module res_pjsip.so not      │
  │  found                               │
  │                                      │
  │  [View Logs]  [Try Again]  [Close]  │
  └─────────────────────────────────────┘

  H. Toast Notifications

  Position: Top-right corner
  Duration: 3 seconds (auto-dismiss)
  Types:

  1. Success (Green):
    - ✅ User created successfully
    - ✅ Configuration applied
    - ✅ User deleted
  2. Error (Red):
    - ❌ Email already in use
    - ❌ Failed to apply configuration
    - ❌ Network error
  3. Info (Blue):
    - ℹ️ Refreshing user list...
    - ℹ️ Extension pool: 958 available
  4. Warning (Orange):
    - ⚠️ Extension pool low (< 100 available)
    - ⚠️ Apply in progress, please wait

  I. Apply History Section

  Collapsible panel at bottom of page

  Each entry shows:
  - Status icon (✅ Success or ❌ Failure)
  - Timestamp (relative: "2 hours ago" or absolute: "Jan 4, 2026 12:30 PM")
  - Triggered by (email)
  - Users/extensions count
  - Clickable to expand and show:
    - Files written
    - Reload results
    - Error details (if failed)

  Pagination: Show last 10, "Load More" button

  ---
  🎨 5. COLOR SCHEME

  Primary Palette

  - Primary Blue: #2563EB (buttons, links)
  - Success Green: #10B981 (success messages, apply status)
  - Warning Orange: #F59E0B (apply button, warnings)
  - Danger Red: #EF4444 (delete, errors)
  - Gray Neutral: #6B7280 (text, borders)

  Background Colors

  - Page Background: #F9FAFB (light gray)
  - Card Background: #FFFFFF (white)
  - Hover State: #EFF6FF (light blue)
  - Border Color: #E5E7EB (light gray)

  Text Colors

  - Primary Text: #111827 (dark gray, almost black)
  - Secondary Text: #6B7280 (medium gray)
  - Muted Text: #9CA3AF (light gray)
  - Link Text: #2563EB (primary blue)

  ---
  📱 6. RESPONSIVE DESIGN

  Desktop (> 1024px)

  - Full layout as shown
  - Table with all columns
  - Statistics cards in single row

  Tablet (768px - 1024px)

  - Stack statistics cards 2x2
  - Table scrolls horizontally
  - Modal dialogs slightly smaller

  Mobile (< 768px)

  - Statistics cards stack vertically
  - Table shows cards instead:
  ┌─────────────────────┐
  │ John Doe            │
  │ john@test.com       │
  │ Extension: 1000     │
  │ [Delete] [Copy]     │
  └─────────────────────┘
  - Action buttons stack vertically
  - Modals full-screen on mobile

  ---
  ⚡ 7. INTERACTIONS & ANIMATIONS

  Button Hover States

  - Slight color darkening
  - Subtle shadow
  - Cursor changes to pointer

  Loading States

  - Spinner for API calls
  - Skeleton screens for table loading
  - Progress bars for apply operation

  Transitions

  - Modal fade-in/fade-out (200ms)
  - Row highlight fade (300ms)
  - Toast slide-in from right (150ms)
  - Smooth scrolling

  Feedback Animations

  - Success: Green checkmark with bounce
  - Error: Red X with shake
  - Delete: Row fade-out and collapse

  ---
  🔐 8. SECURITY CONSIDERATIONS

  Current (MVP):

  - No authentication (trusted network only)
  - All users have admin access

  Future Enhancements:

  - Login page with username/password
  - Session management
  - Role-based access control (admin vs. read-only)
  - API key authentication
  - HTTPS enforcement

  Data Handling:

  - SIP secrets shown with "Copy" button (not displayed in plain text by default)
  - Click "👁️ Show" to reveal secret
  - Auto-hide after 5 seconds

  ---
  🧪 9. USER FLOWS

  Flow 1: Create New User

  1. Click "+ Add User" button
  2. Modal opens
  3. Fill in name and email
  4. Click "Create User"
  5. Modal closes
  6. Toast shows success
  7. Table refreshes
  8. New user appears at top (highlighted)
  9. User sees assigned extension number in toast

  Time: ~10 seconds

  Flow 2: Apply Configuration

  1. Click "⚡ Apply Configuration"
  2. Confirmation modal shows summary
  3. Click "Apply Now"
  4. Progress modal shows steps
  5. Success modal shows results
  6. Click "Close"
  7. Apply history updates
  8. Statistics refresh

  Time: ~5-10 seconds

  Flow 3: Delete User

  1. Click 🗑️ next to user
  2. Confirmation modal shows user details
  3. Click "Delete"
  4. Modal closes
  5. Row fades out and disappears
  6. Toast shows success
  7. Statistics update

  Time: ~5 seconds

  ---
  🛠️ 10. TECHNOLOGY STACK

  Frontend:

  - HTML5: Semantic markup
  - CSS3: Modern styling with Flexbox/Grid
  - JavaScript (Vanilla): No framework needed (lightweight)
  - Bootstrap 5: UI components and responsive grid
  - Font Awesome: Icons
  - Fetch API: AJAX calls to backend

  Why No Framework?

  - Simpler deployment (single HTML file)
  - No build process required
  - Faster loading
  - Easier to customize
  - Perfect for this use case

  File Structure:

  /opt/pbx-portal/
  ├── src/
  │   └── main.py (existing backend)
  ├── static/
  │   ├── index.html (admin panel)
  │   ├── css/
  │   │   └── styles.css
  │   └── js/
  │       └── app.js

  ---
  📊 11. FEATURES SUMMARY

  Phase 1 (MVP - What I'll Build Now):

  - ✅ User list table with search
  - ✅ Add user modal
  - ✅ Delete user with confirmation
  - ✅ Apply configuration with progress
  - ✅ Statistics dashboard
  - ✅ Toast notifications
  - ✅ Apply history
  - ✅ Responsive design
  - ✅ Copy SIP secret to clipboard

  Phase 2 (Future Enhancements):

  - 🔮 Edit user (update name/email)
  - 🔮 Bulk operations (delete multiple)
  - 🔮 Export users to CSV
  - 🔮 Advanced filtering
  - 🔮 Dark mode toggle
  - 🔮 User profile pages
  - 🔮 Real-time updates (WebSocket)
  - 🔮 Call statistics integration

  ---
  📝 12. ACCEPTANCE CRITERIA

  ✅ Must Have:
  1. Users can create a user in < 10 seconds
  2. Users can delete a user in < 5 seconds
  3. Users can apply config in < 10 seconds
  4. All operations show clear success/error messages
  5. Works on Chrome, Firefox, Safari, Edge
  6. Works on mobile phones (iOS/Android)
  7. No page refreshes (single-page app)
  8. Loading states for all async operations

  ✅ Performance:
  - Page loads in < 2 seconds
  - API calls complete in < 1 second
  - Animations smooth (60 FPS)
  - Works with 1000+ users without lag

  --