# MODDY Staff Permissions System

## Overview

The MODDY staff system provides a comprehensive role-based permission system for managing staff members with different levels of access and responsibilities.

## Command Syntax

All staff commands use the following syntax:

```
<@&1386452009678278818> [type].[command] [arguments]
```

### Components:

- `<@&1386452009678278818>` - Staff command prefix (role mention)
- `[type]` - Command type prefix (see below)
- `[command]` - Command name
- `[arguments]` - Optional command arguments

### Command Type Prefixes:

| Prefix | Type | Description | Required Roles |
|--------|------|-------------|----------------|
| `t.` | Team | Commands common to all staff | All staff members |
| `m.` | Management | Staff management commands | Manager |
| `d.` | Developer | Developer commands | Dev |
| `mod.` | Moderator | Moderation commands | Manager, Supervisor_Mod, Moderator |
| `sup.` | Support | Support commands | Manager, Supervisor_Sup, Support |
| `com.` | Communication | Communication commands | Manager, Supervisor_Com, Communication |

## Staff Roles

### Hierarchy

The staff hierarchy (from highest to lowest):

1. **Dev** (apart from hierarchy - auto-assigned to Discord dev team members)
2. **Manager**
3. **Supervisor** (Mod/Com/Support)
4. **Staff** (Moderator/Communication/Support)

### Role Descriptions:

#### Dev
- Automatically assigned to Discord Developer Portal team members
- Has access to all commands
- Can assign any role
- Can modify any staff member

#### Manager
- Can manage all staff members
- Can assign any non-dev role
- Has access to all non-dev commands
- Automatically assigned to Discord dev team members

#### Supervisor (Mod/Com/Support)
- Supervises their respective department
- Can assign staff roles in their department
- Cannot modify managers or other supervisors
- Has access to their department's commands

#### Staff (Moderator/Communication/Support)
- Standard staff members in their department
- Can use their department's commands
- Cannot manage other staff members

## Management Commands (m. prefix)

### m.rank @user

Add a user to the staff team.

**Usage:**
```
<@&1386452009678278818> m.rank @user
```

**Permission:** Manager or Supervisor

**Example:**
```
<@&1386452009678278818> m.rank @JohnDoe
```

Opens an interactive role selection menu to assign roles to the new staff member.

### m.setstaff @user

Manage an existing staff member's permissions.

**Usage:**
```
<@&1386452009678278818> m.setstaff @user
```

**Permission:** Manager or Supervisor (can only modify staff below their level)

**Example:**
```
<@&1386452009678278818> m.setstaff @JohnDoe
```

Features:
- Edit roles
- Manage command restrictions (deny specific commands)

### m.stafflist

List all staff members organized by role.

**Usage:**
```
<@&1386452009678278818> m.stafflist
```

**Permission:** Manager or Supervisor

### m.staffinfo [@user]

Show detailed information about a staff member. If no user is mentioned, shows your own information.

**Usage:**
```
<@&1386452009678278818> m.staffinfo @user
<@&1386452009678278818> m.staffinfo
```

**Permission:** All staff members

## Team Commands (t. prefix)

Available to all staff members.

### t.help

Show available commands based on your permissions.

**Usage:**
```
<@&1386452009678278818> t.help
```

### t.invite [server_id]

Get an invite link to a server where MODDY is present.

**Usage:**
```
<@&1386452009678278818> t.invite 1234567890
```

Creates a 7-day invite with 5 max uses.

### t.serverinfo [server_id]

Get detailed information about a server where MODDY is present.

**Usage:**
```
<@&1386452009678278818> t.serverinfo 1234567890
```

Shows:
- Basic server information
- Member statistics
- Channel counts
- Boost status
- Server features

## Developer Commands (d. prefix)

Exclusive to Discord Dev Portal team members.

### d.reload [extension]

Reload bot extensions. Use "all" to reload everything.

**Usage:**
```
<@&1386452009678278818> d.reload all
<@&1386452009678278818> d.reload staff.team_commands
```

### d.shutdown

Shutdown the bot.

**Usage:**
```
<@&1386452009678278818> d.shutdown
```

### d.stats

Show comprehensive bot statistics including uptime, resources, and database stats.

**Usage:**
```
<@&1386452009678278818> d.stats
```

### d.sql [query]

Execute SQL queries directly on the database. Requires confirmation for dangerous operations.

**Usage:**
```
<@&1386452009678278818> d.sql SELECT * FROM users LIMIT 10
```

## Moderator Commands (mod. prefix)

Available to Manager, Supervisor_Mod, and Moderator.

### mod.blacklist @user [reason]

Blacklist a user from using MODDY.

**Usage:**
```
<@&1386452009678278818> mod.blacklist @user Spam and abuse
```

### mod.unblacklist @user [reason]

Remove a user from the blacklist.

**Usage:**
```
<@&1386452009678278818> mod.unblacklist @user Appeal accepted
```

### mod.userinfo @user

Get detailed information about a user including database attributes and shared servers.

**Usage:**
```
<@&1386452009678278818> mod.userinfo @user
```

### mod.guildinfo [guild_id]

Get detailed information about a guild including database attributes.

**Usage:**
```
<@&1386452009678278818> mod.guildinfo 1234567890
```

## Support Commands (sup. prefix)

Available to Manager, Supervisor_Sup, and Support. *In development.*

## Communication Commands (com. prefix)

Available to Manager, Supervisor_Com, and Communication. *In development.*

## Permission Rules

### Hierarchy Rules:

1. **Supervisors and Managers cannot:**
   - Assign permissions they don't have
   - Modify permissions of staff at the same level or above
   - A Supervisor cannot modify another Supervisor or a Manager

2. **Developers (Discord Dev Team):**
   - Automatically get Manager + Dev roles
   - Can modify anyone (except other devs are always Manager+Dev)
   - Cannot be removed from Manager+Dev roles

3. **Command Restrictions:**
   - Even if you have access to a command type, specific commands can be denied
   - Denied commands are managed via `m.setstaff`

### TEAM Attribute:

All staff members automatically receive the `TEAM` attribute in the database. This attribute is:
- Automatically added when roles are assigned via `m.rank`
- Automatically removed when all roles are removed
- Used to identify staff members system-wide

## Database Schema

### staff_permissions Table

```sql
CREATE TABLE staff_permissions (
    user_id BIGINT PRIMARY KEY,
    roles JSONB DEFAULT '[]'::jsonb,
    denied_commands JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by BIGINT,
    updated_by BIGINT
)
```

### Roles Format:

```json
["Manager", "Dev"]
["Supervisor_Mod"]
["Moderator"]
```

### Denied Commands Format:

```json
["mod.ban", "mod.kick", "t.invite"]
```

## UI/UX Design

### Display Format:

All staff commands use **Discord Components V2** (colored components), **NOT embeds**.

Features:
- Professional appearance
- Color-coded responses (success=green, error=red, info=blue)
- Interactive buttons and select menus
- Ephemeral messages where appropriate

### Language:

All staff commands are in **English only** and do **NOT** use the i18n system.

## Implementation Details

### Files:

- `/utils/staff_permissions.py` - Permission manager and role hierarchy
- `/staff/staff_manager.py` - Management commands (m. prefix)
- `/staff/team_commands.py` - Team commands (t. prefix)
- `/staff/dev_commands.py` - Developer commands (d. prefix)
- `/staff/moderator_commands.py` - Moderator commands (mod. prefix)
- `/staff/support_commands.py` - Support commands (sup. prefix)
- `/staff/communication_commands.py` - Communication commands (com. prefix)
- `/database.py` - Database methods for staff permissions

### Key Classes:

- `StaffPermissionManager` - Main permission checking logic
- `StaffRole` - Enum of available roles
- `CommandType` - Enum of command type prefixes

### Auto-initialization:

When the bot starts:
1. Staff permissions system is initialized
2. Discord dev team members are fetched
3. Dev team members automatically get DEVELOPER attribute + Manager+Dev roles

## Migration from Old System

The old system used:
- Simple `is_developer()` check
- `cog_check()` in each staff cog

The new system:
- Role-based permissions with hierarchy
- Granular command access control
- Interactive management UI
- Database-backed permissions

### Backward Compatibility:

- Old staff commands (developer-only) still work
- Developers automatically get all permissions
- Can be migrated gradually to new command syntax

## Examples

### Adding a Moderator:

```
<@&1386452009678278818> m.rank @NewMod
```

Select "Moderator" role in the menu, click Confirm.

### Managing a Staff Member:

```
<@&1386452009678278818> m.setstaff @ExistingStaff
```

Click "Edit Roles" to change roles, or "Manage Command Restrictions" to deny specific commands.

### Getting a Server Invite:

```
<@&1386452009678278818> t.invite 1234567890
```

### Checking Staff List:

```
<@&1386452009678278818> m.stafflist
```

Shows all staff members organized by role.

## Security Considerations

1. **Role Mention Prefix:** The `<@&1386452009678278818>` prefix prevents accidental command execution
2. **Hierarchy Enforcement:** Lower-level staff cannot modify higher-level staff
3. **Command Denial:** Specific commands can be denied even if role allows them
4. **Audit Trail:** All permission changes are logged with `created_by` and `updated_by`
5. **Dev Team Lock:** Discord dev team members cannot be removed from Manager+Dev roles

## Future Enhancements

Potential additions:
- Department-specific commands (mod., sup., com. prefixes)
- Permission templates for quick role assignment
- Audit log viewer
- Bulk staff management
- Permission inheritance
- Temporary permissions/roles
