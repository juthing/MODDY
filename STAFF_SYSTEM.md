# MODDY Staff Permissions System

## Overview

The MODDY staff system provides a comprehensive role-based permission system for managing staff members with different levels of access and responsibilities.

## Command Syntax

All staff commands use the following syntax:

```
<@1373916203814490194> [type].[command] [arguments]
```

### Components:

- `<@1373916203814490194>` - Staff command prefix (bot mention)
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

1. **Super Admin** (User ID: 1164597199594852395 - bypasses all permission checks)
2. **Dev** (apart from hierarchy - auto-assigned to Discord dev team members)
3. **Manager**
4. **Supervisor** (Mod/Com/Support)
5. **Staff** (Moderator/Communication/Support)

### Role Descriptions:

#### Super Admin
- Hard-coded user ID: 1164597199594852395
- Bypasses **all** permission checks
- Can assign any role, even those they don't have
- Can modify any staff member, including managers and devs
- Has absolute control over the entire system
- Cannot be restricted or limited in any way

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
<@1373916203814490194> m.rank @user
```

**Permission:** Manager or Supervisor

**Example:**
```
<@1373916203814490194> m.rank @JohnDoe
```

Opens an interactive role selection menu to assign roles to the new staff member.

### m.setstaff @user

Manage an existing staff member's permissions.

**Usage:**
```
<@1373916203814490194> m.setstaff @user
```

**Permission:** Manager or Supervisor (can only modify staff below their level)

**Example:**
```
<@1373916203814490194> m.setstaff @JohnDoe
```

Features:
- Edit roles
- Manage command restrictions (deny specific commands)

### m.stafflist

List all staff members organized by role.

**Usage:**
```
<@1373916203814490194> m.stafflist
```

**Permission:** Manager or Supervisor

### m.staffinfo [@user]

Show detailed information about a staff member. If no user is mentioned, shows your own information.

**Usage:**
```
<@1373916203814490194> m.staffinfo @user
<@1373916203814490194> m.staffinfo
```

**Permission:** All staff members

## Team Commands (t. prefix)

Available to all staff members.

### t.help

Show available commands based on your permissions.

**Usage:**
```
<@1373916203814490194> t.help
```

### t.invite [server_id]

Get an invite link to a server where MODDY is present.

**Usage:**
```
<@1373916203814490194> t.invite 1234567890
```

Creates a 7-day invite with 5 max uses.

### t.serverinfo [server_id]

Get detailed information about a server where MODDY is present.

**Usage:**
```
<@1373916203814490194> t.serverinfo 1234567890
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
<@1373916203814490194> d.reload all
<@1373916203814490194> d.reload staff.team_commands
```

### d.shutdown

Shutdown the bot.

**Usage:**
```
<@1373916203814490194> d.shutdown
```

### d.stats

Show comprehensive bot statistics including uptime, resources, and database stats.

**Usage:**
```
<@1373916203814490194> d.stats
```

### d.sql [query]

Execute SQL queries directly on the database. Requires confirmation for dangerous operations.

**Usage:**
```
<@1373916203814490194> d.sql SELECT * FROM users LIMIT 10
```

### d.jsk [code]

Execute Python code directly in the bot's runtime environment. Supports async/await and has access to bot context.

**Usage:**
```
<@1373916203814490194> d.jsk print("Hello World")
<@1373916203814490194> d.jsk return len(bot.guilds)
<@1373916203814490194> d.jsk await message.channel.send("Test")
```

**Available Variables:**
- `bot` - Bot instance
- `message` - Message object
- `channel` - Current channel
- `author` - Command author
- `guild` - Current guild
- `db` - Database instance
- `discord`, `commands`, `asyncio`, `datetime`, `timezone` - Common modules

**Code Blocks:**
You can use Python code blocks for multi-line code:
```
<@1373916203814490194> d.jsk ```python
guilds = bot.guilds
print(f"Bot is in {len(guilds)} guilds")
for guild in guilds[:5]:
    print(f"- {guild.name}")
\```
```

## Moderator Commands (mod. prefix)

Available to Manager, Supervisor_Mod, and Moderator.

### mod.blacklist @user [reason]

Blacklist a user from using MODDY.

**Usage:**
```
<@1373916203814490194> mod.blacklist @user Spam and abuse
```

### mod.unblacklist @user [reason]

Remove a user from the blacklist.

**Usage:**
```
<@1373916203814490194> mod.unblacklist @user Appeal accepted
```

### mod.userinfo @user

Get detailed information about a user including database attributes and shared servers.

**Usage:**
```
<@1373916203814490194> mod.userinfo @user
```

### mod.guildinfo [guild_id]

Get detailed information about a guild including database attributes.

**Usage:**
```
<@1373916203814490194> mod.guildinfo 1234567890
```

## Support Commands (sup. prefix)

Available to Manager, Supervisor_Sup, and Support. *In development.*

## Communication Commands (com. prefix)

Available to Manager, Supervisor_Com, and Communication. *In development.*

## Permission Rules

### Hierarchy Rules:

1. **Super Admin (User ID: 1164597199594852395):**
   - Bypasses **ALL** permission checks
   - Can assign any role, even Manager and Dev roles
   - Can modify any staff member, including themselves
   - Cannot be restricted by denied commands
   - Has absolute control over the entire system

2. **Supervisors and Managers cannot:**
   - Assign permissions they don't have (except Super Admin)
   - Modify permissions of staff at the same level or above
   - A Supervisor cannot modify another Supervisor or a Manager

3. **Developers (Discord Dev Team):**
   - Automatically get Manager + Dev roles
   - Can modify anyone (except other devs are always Manager+Dev, and Super Admin can modify anyone)
   - Cannot be removed from Manager+Dev roles

4. **Command Restrictions:**
   - Even if you have access to a command type, specific commands can be denied
   - Denied commands are managed via `m.setstaff`
   - Super Admin bypasses all command restrictions

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

Staff commands use **Discord Components V2** (LayoutView, Container, TextDisplay, Separator) for modern structured messages.

Features:
- Clean, structured layout using Components V2
- Error, success, info, and warning message helpers
- Interactive buttons and select menus (still using embeds for compatibility)
- Messages **reply** to the command message (not sent in channel)
- Messages are **NOT automatically deleted** - they remain visible

### Message Behavior:

- All staff command responses use `message.reply()` instead of `message.channel.send()`
- `mention_author=False` is used to avoid unnecessary mentions
- No automatic deletion (`delete_after` is not used)
- This ensures command history is preserved and visible to all staff

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

### Key Classes and Constants:

- `StaffPermissionManager` - Main permission checking logic
  - `STAFF_PREFIX` - Bot mention: `<@1373916203814490194>`
  - `SUPER_ADMIN_ID` - Super admin user ID: `1164597199594852395`
- `StaffRole` - Enum of available roles
- `CommandType` - Enum of command type prefixes
- Components V2 helpers in `utils/components_v2.py`:
  - `create_error_message()` - Create error messages
  - `create_success_message()` - Create success messages
  - `create_info_message()` - Create info messages
  - `create_warning_message()` - Create warning messages
  - `create_staff_info_message()` - Create staff information displays

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
<@1373916203814490194> m.rank @NewMod
```

Select "Moderator" role in the menu, click Confirm.

### Managing a Staff Member:

```
<@1373916203814490194> m.setstaff @ExistingStaff
```

Click "Edit Roles" to change roles, or "Manage Command Restrictions" to deny specific commands.

### Getting a Server Invite:

```
<@1373916203814490194> t.invite 1234567890
```

### Checking Staff List:

```
<@1373916203814490194> m.stafflist
```

Shows all staff members organized by role.

## Security Considerations

1. **Bot Mention Prefix:** The `<@1373916203814490194>` prefix prevents accidental command execution
2. **Super Admin:** User ID `1164597199594852395` has absolute control and bypasses all checks (hard-coded)
3. **Hierarchy Enforcement:** Lower-level staff cannot modify higher-level staff (except Super Admin)
4. **Command Denial:** Specific commands can be denied even if role allows them (not applicable to Super Admin)
5. **Audit Trail:** All permission changes are logged with `created_by` and `updated_by`
6. **Dev Team Lock:** Discord dev team members cannot be removed from Manager+Dev roles
7. **Database Failsafe:** If database is unavailable, only Super Admin and Discord dev team members can use commands

## Future Enhancements

Potential additions:
- Department-specific commands (mod., sup., com. prefixes)
- Permission templates for quick role assignment
- Audit log viewer
- Bulk staff management
- Permission inheritance
- Temporary permissions/roles
