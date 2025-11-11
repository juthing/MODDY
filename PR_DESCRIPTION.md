# feat(staff): Implement role-based permissions system with granular control

## Summary
Major overhaul of the staff permission system implementing a role-based architecture with granular permission control.

## Key Features

### Role-Based Permission System
- **Roles have no power by default** - All permissions must be explicitly granted
- **Granular control** through interactive dropdown menus in Components V2
- **Common permissions** that apply to all assigned roles (flex, invite, serverinfo)
- **Role-specific permissions** for each staff role:
  - **Moderator:** blacklist, unblacklist, userinfo, guildinfo
  - **Support:** ticket_view, ticket_close, ticket_create
  - **Communication:** announce, broadcast
  - **Manager:** rank, unrank, setstaff, stafflist, staffinfo

### Interactive Interface
- Dynamic dropdown menus that appear based on selected roles
- Real-time updates when roles are modified
- Separate menus for common permissions and role-specific permissions
- Save/Cancel options with validation

### Message Behavior Improvements
- **Auto-deletion:** Bot responses are automatically deleted when command messages are deleted
- **Clean interface:** Removed all footers ("Requested by...", "Removed by...", etc.)
- Cleaner, more natural command interaction

## Database Changes
- Added `role_permissions` JSONB column to `staff_permissions` table
- Automatic migration on bot startup
- Stores permissions per role + common permissions:
  ```json
  {
    "Moderator": ["blacklist", "unblacklist", "userinfo", "guildinfo"],
    "Support": ["ticket_view", "ticket_close"],
    "common": ["flex", "invite", "serverinfo"]
  }
  ```

## Code Architecture
- **New file:** `utils/staff_role_permissions.py` - Centralized permission definitions
- **New class:** `StaffPermissionsManagementView` - Comprehensive permission management UI
- **Message tracking:** Implemented in all staff command cogs for auto-deletion feature
- **New database methods:** `set_role_permissions()` and `get_role_permissions()`

## Modified Files
- `database.py` - Added role_permissions column and methods
- `staff/staff_manager.py` - New permission management system + message tracking
- `staff/team_commands.py` - Added message deletion tracking
- `staff/moderator_commands.py` - Added message deletion tracking
- `STAFF_SYSTEM.md` - Complete documentation update

## Breaking Changes
- Staff roles now require explicit permission assignment through `m.setstaff`
- Old `denied_commands` system is deprecated in favor of role permissions

## Test Plan
- [x] m.setstaff displays role selection menu
- [x] Role selection triggers permission menus
- [x] Common permissions menu appears when roles are selected
- [x] Role-specific permission menus appear for each role
- [x] Save button correctly stores all permissions
- [x] Message deletion triggers response deletion
- [x] All footers removed from messages

## Documentation
- Updated STAFF_SYSTEM.md with complete documentation
- Added detailed explanation of role permissions format
- Documented auto-deletion feature and message behavior

## Fixes
- Fixed missing json import that caused NameError when saving permissions

## Commits
- `cbc0d21` - feat(staff): Implement role-based permissions system with granular control
- `abbeb28` - fix(staff): Add missing json import in staff_manager.py
