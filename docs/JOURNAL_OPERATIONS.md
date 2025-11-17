# Journal Operations in Import Script

This document lists all steps and actions related to journal entries in `import_work_packages.py`.

## Summary

The script **ONLY MODIFIES** journal entries (timestamps, user_id, validity_period). It **NEVER DELETES** any journal entries.

## Performance Optimizations

All journal operations are **batched for optimal performance**:
- Updates are grouped by common values (timestamp, user_id) to minimize SQL statements
- Uses `WHERE IN` clauses to update multiple records in a single UPDATE statement
- Reduces database round-trips from N individual updates to ~1-10 batched updates

---

## Step 18: Update time entry logged_by field

**Location**: Lines 6857-6874  
**Function**: `update_time_entry_logged_by_batch()` (Lines 1175-1259)

### Journal Operations:
1. **Update `journals.user_id` for TimeEntry journals** (BATCHED)
   - **Action**: `UPDATE journals SET user_id = {user_id} WHERE journable_type='TimeEntry' AND journable_id IN ({entry_id_list})`
   - **Purpose**: Set the author (user_id) of the time entry journal to match the person who logged the time
   - **When**: For all time entries that need their `logged_by` field corrected
   - **Optimization**: Groups updates by `user_id` and uses `WHERE IN` to batch multiple entries per user
   - **Note**: Only updates if the `user_id` column exists in the `journals` table

---

## Step 19: Adjust activity history

**Location**: Lines 6876-6913  
**Function**: `apply_history_adjustments()` (Lines 3288-3466)

### Journal Operations:

#### 1. Update WorkPackage Journal Timestamps and Authors (COMBINED & BATCHED)
   - **Action**: `UPDATE journals SET created_at='{ts}', updated_at='{ts}', validity_period=tstzrange('{ts}', NULL), user_id={author_id} WHERE journable_type='WorkPackage' AND journable_id IN ({wp_id_list})`
   - **Purpose**: Set all work package journal entries to have the same creation timestamp (random time between 8:00 AM - 12:00 PM) and author
   - **When**: For all imported work packages
   - **Optimization**: 
     - Combines timestamp and user_id updates into a single UPDATE statement
     - Groups by (timestamp, author_id) and uses `WHERE IN` to batch multiple work packages
   - **Fields Modified**:
     - `created_at`: Set to random creation time
     - `updated_at`: Set to random creation time
     - `validity_period`: Set to start from creation time
     - `user_id`: Set to assignee_id or current_user_id (admin)

#### 2. Update TimeEntry Journal Timestamps (BATCHED)
   - **Action**: `UPDATE journals SET created_at='{ts}', updated_at='{ts}', validity_period=tstzrange('{ts}', NULL) WHERE journable_type='TimeEntry' AND journable_id IN ({te_id_list})`
   - **Purpose**: Set time entry journal timestamps to match the time entry's spent_on date (with offset for multiple entries on same day)
   - **When**: For all time entries
   - **Optimization**: Groups by timestamp and uses `WHERE IN` to batch multiple time entries
   - **Fields Modified**:
     - `created_at`: Set to time entry timestamp
     - `updated_at`: Set to time entry timestamp
     - `validity_period`: Set to start from time entry timestamp

---

## Step 20: Update project creation dates

**Location**: Lines 6915-6936  
**Function**: `update_project_creation_dates()` (Lines 3184-3285) and `scan_and_update_all_project_dates()` (Lines 2983-3182)

### Journal Operations:

#### 1. Update Project Journal Creation Timestamps (Version 1) (BATCHED)
   - **Action**: `UPDATE journals SET created_at='{ts}', updated_at='{ts}', validity_period=tstzrange('{ts}', NULL) WHERE journable_type='Project' AND journable_id IN ({proj_id_list}) AND version=1`
   - **Purpose**: Set project journal version 1 (initial creation) to have the earliest date from related work packages or time entries
   - **When**: For all projects that have imported work packages
   - **Optimization**: Groups projects by timestamp and uses `WHERE IN` to batch multiple projects
   - **Fields Modified**:
     - `created_at`: Set to earliest work/time entry date
     - `updated_at`: Set to earliest work/time entry date
     - `validity_period`: Set to start from earliest date

#### 2. Alternative Update (in `scan_and_update_all_project_dates`)
   - **Action**: Similar UPDATE statement but handles exclusion constraint differently
   - **Purpose**: Same as above, but uses a different approach to handle PostgreSQL exclusion constraints
   - **When**: When scanning all projects (not just imported ones)

---

## Summary of Journal Modifications

### Fields Modified:
1. **`created_at`**: Timestamp when the journal entry was created
2. **`updated_at`**: Timestamp when the journal entry was last updated
3. **`user_id`**: User who created/author of the journal entry
4. **`validity_period`**: Time range for which the journal entry is valid

### Journal Types Modified:
1. **WorkPackage journals** (`journable_type='WorkPackage'`)
   - All versions updated with creation timestamps
   - All versions updated with author (user_id)

2. **TimeEntry journals** (`journable_type='TimeEntry'`)
   - Updated with time entry timestamps
   - Updated with author (user_id) to match logged_by

3. **Project journals** (`journable_type='Project'`)
   - Version 1 updated with earliest work/time entry date

### Operations NOT Performed:
- ❌ **NO DELETE operations** on journals
- ❌ **NO INSERT operations** to create new journal entries
- ❌ **NO cleanup** of journal entries
- ❌ **NO removal** of "Author changed" messages
- ❌ **NO creation** of status change journal entries

### Operations Performed:
- ✅ **UPDATE timestamps** only
- ✅ **UPDATE user_id** (author) only
- ✅ **UPDATE validity_period** only

---

## Code Locations

| Step | Function | Lines | Description |
|------|----------|-------|-------------|
| 18 | `update_time_entry_logged_by_batch()` | 1175-1281 | Update TimeEntry journal user_id (BATCHED) |
| 19 | `apply_history_adjustments()` | 3288-3579 | Update WorkPackage and TimeEntry journal timestamps and authors (BATCHED) |
| 20 | `update_project_creation_dates()` | 3195-3293 | Update Project journal version 1 timestamps (BATCHED) |
| 20 | `scan_and_update_all_project_dates()` | 2983-3192 | Scan and update all project journals |

