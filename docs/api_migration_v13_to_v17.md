# OpenProject API Migration Guide: v13 → v17

> **Purpose**: This document captures all API-related changes, breaking changes, and new features from OpenProject v13 through v17. Use this as a reference when implementing the new `OpenProjectV17Provider`.
>
> **Last Updated**: January 15, 2026
> **OpenProject v17.0.0 Released**: January 14, 2026

---

## Table of Contents

1. [Version Compatibility Matrix](#1-version-compatibility-matrix)
2. [Breaking API Changes](#2-breaking-api-changes)
3. [New API Endpoints](#3-new-api-endpoints)
4. [Time Entry API Changes](#4-time-entry-api-changes)
5. [Work Package API Changes](#5-work-package-api-changes)
6. [Authentication Changes](#6-authentication-changes)
7. [Database & Infrastructure Changes](#7-database--infrastructure-changes)
8. [Implementation Recommendations](#8-implementation-recommendations)

---

## 1. Version Compatibility Matrix

| Feature | v13.x | v14.x | v15.x | v16.x | v17.x |
|---------|-------|-------|-------|-------|-------|
| API Version | v3 | v3 | v3 | v3 | v3 |
| PostgreSQL | 13+ | 13+ | 13+ | 13+ | **17.0 (REQUIRED)** |
| HAL+JSON | ✅ | ✅ | ✅ | ✅ | ✅ |
| OpenAPI Spec | 3.0 | 3.0 | 3.0 | 3.1 | 3.1 |
| `delay` attribute | ✅ | ❌ (renamed to `lag`) | ❌ | ❌ | ❌ |
| `available_responsibles` | ✅ | ❌ (removed) | ❌ | ❌ | ❌ |
| Time Entry Start/End Time | ❌ | ❌ | ❌ | ✅ | ✅ |
| Built-in OAuth App | ❌ | ❌ | ❌ | ❌ | ✅ |
| Real-time Documents | ❌ | ❌ | ❌ | ❌ | ✅ |

> [!CAUTION]
> **PostgreSQL 17 is MANDATORY for OpenProject v17**
>
> OpenProject v17 uses PostgreSQL 17-specific features like `transaction_timeout`. Using PostgreSQL 15 or 16 will cause the migration to fail with:
> ```
> psql:/app/db/structure.sql:4: ERROR: unrecognized configuration parameter "transaction_timeout"
> ```

---

## 2. Breaking API Changes

### 2.1. v14.0.0: Relations API - `delay` → `lag`

**BREAKING CHANGE**

In the Relations API, the attribute `delay` has been renamed to `lag` to align with project management terminology.

```diff
// Work Package Relations
{
  "_type": "Relation",
  "type": "follows",
-  "delay": 2,
+  "lag": 2,
  "_links": { ... }
}
```

**Provider Impact**:
- Update any code that reads/writes the `delay` field in relation objects
- The `lag` attribute represents the time offset (in days) between related work packages

**Reference**: [#44054](https://community.openproject.org/work_packages/44054)

---

### 2.2. v14.0.0: Removed `available_responsibles` Endpoint

**BREAKING CHANGE**

The `/api/v3/projects/{id}/available_responsibles` endpoint has been **removed**.

**Migration**:
```diff
// Before v14
- GET /api/v3/projects/{id}/available_responsibles

// v14+: Use available_assignees instead (identical results)
+ GET /api/v3/projects/{id}/available_assignees
```

**Provider Impact**:
- Replace any calls to `available_responsibles` with `available_assignees`
- The response format is identical

---

### 2.3. v14.0.0: Permission System Overhaul (Internal)

In version 13.1/14.0, OpenProject overhauled the internal permission handling to allow permissions at the resource level (e.g., individual work packages).

**Removed Deprecated Methods**:
- `User#allowed_to?`
- `User#allowed_to_globally?`
- `User#allowed_to_in_project?`

**Provider Impact**:
- If using custom scripts or plugins that rely on these internal Ruby methods, switch to the new resource-aware permission checks.
- API-wise, this is reflected in the context-sensitive `_links` (see [HATEOAS Structural Guarantees](#55-hateoas-structural-guarantees-api-v3)).

---

---

### 2.3. v16.0.0: JWT Scope Requirement for API v3

**BREAKING CHANGE**

Starting with v16.0.0, all JWT tokens issued by OpenID Connect providers **must** include the `api_v3` scope for API requests.

```json
// JWT Token must include:
{
  "scope": "api_v3 openid profile email"
}
```

**Provider Impact**:
- If using OIDC authentication, ensure the provider is configured to issue tokens with `api_v3` scope
- Affects integrations with external identity providers (Keycloak, Auth0, Azure AD, etc.)

**Reference**: [OpenProject 16.0.0 Release Notes](https://www.openproject.org/docs/release-notes/16-0-0/)

---

### 2.4. v14.0.0: Nomenclature - Project Attributes

Project-specific custom fields are now formally referred to as **'Project attributes'**. They have a dedicated administration page and are edited directly on the project overview page.


---

## 3. New API Endpoints

### 3.1. v17.0.0: Documents API (Real-time Collaboration)

New endpoints for real-time document collaboration:

```
GET    /api/v3/documents
GET    /api/v3/documents/{id}
POST   /api/v3/documents
PATCH  /api/v3/documents/{id}
DELETE /api/v3/documents/{id}
```

**New Features**:
- Documents use BlockNote editor (replaces CKEditor when Hocuspocus is available)
- Work package integration via slash commands
- Unified URL format: `/documents/{id}` for both editing and viewing

**Provider Consideration**:
- Document content may be stored in a different format (BlockNote JSON vs CKEditor HTML)
- Real-time collaboration requires Hocuspocus server (Docker setups include this)

---

### 3.2. v17.0.0: Enhanced Meetings API

Meetings API has been significantly enhanced:

```
// New endpoints/features
GET /api/v3/meetings/{id}/agenda_items
POST /api/v3/meetings/{id}/agenda_items
PATCH /api/v3/agenda_items/{id}

// New fields on Meeting resources
{
  "draft": true,           // New: Draft mode support
  "outcomes": [...],       // New: Multiple outcomes per agenda item
  "ical_subscription": "..." // New: Unified iCal subscription URL
}
```

**New Meeting Features**:
- Draft mode (meetings can be prepared before sending invitations)
- Presentation mode (full-screen view)
- Multiple text-based outcomes per agenda item
- Unified "My meetings" iCal subscription

---

### 3.3. v16.0.0: Time Tracking Module Endpoints

Enhanced time entry endpoints with start/end time support:

```
GET  /api/v3/time_entries
POST /api/v3/time_entries
```

**New Fields in v16+**:
```json
{
  "id": 123,
  "hours": "PT2H30M",
  "spentOn": "2026-01-15",
  "startTime": "09:00",     // NEW in v16
  "endTime": "11:30",       // NEW in v16
  "comment": { "raw": "..." },
  "_links": {
    "workPackage": { "href": "/api/v3/work_packages/456" },
    "user": { "href": "/api/v3/users/789" },
    "activity": { "href": "/api/v3/time_entries/activities/1" }
  }
}
```

**Provider Impact**:
- Parse `startTime` and `endTime` fields when present
- These fields are optional in v16 but may become mandatory if admin enables "Require exact times"

---

## 4. Time Entry API Changes

### 4.1. v16.0.0: Exact Time Tracking

**New Configuration Options** (Admin setting):
- `allow_exact_time_tracking`: Enables start/end time fields
- `require_exact_times`: Makes start/end time mandatory

**Response Format Evolution**:

```json
// v13-v15: Basic time entry
{
  "hours": "PT8H",
  "spentOn": "2026-01-15"
}

// v16+: Enhanced time entry (when exact tracking enabled)
{
  "hours": "PT8H",
  "spentOn": "2026-01-15",
  "startTime": "08:00",
  "endTime": "16:00"
}
```

### 4.2. ISO 8601 Duration Format (Unchanged)

The `hours` field continues to use ISO 8601 duration format across all versions:

```python
# Duration parsing (still valid in v17)
def _parse_duration_to_hours(duration_str: str) -> float:
    import re
    days = re.search(r'(\d+)D', duration_str)
    hours = re.search(r'(\d+)H', duration_str)
    minutes = re.search(r'(\d+)M', duration_str)
    
    total = 0.0
    if days: total += float(days.group(1)) * 24.0
    if hours: total += float(hours.group(1))
    if minutes: total += float(minutes.group(1)) / 60.0
    return total
```

---

## 5. Work Package API Changes

### 5.1. v14.0.0: Progress Reporting Overhaul

**Major Behavioral Change** (Not a breaking API change, but affects data interpretation):

- `% Complete` is now **automatically calculated** based on `Work` and `Remaining Work`
- In Work-based mode: `percentageDone = (work - remainingWork) / work * 100`
- The field is **read-only** in Work-based progress reporting mode

**API Response**:
```json
{
  "estimatedTime": "PT40H",      // "Work" in UI
  "remainingTime": "PT10H",      // "Remaining Work" in UI
  "percentageDone": 75,          // Auto-calculated, may be read-only
  "spentTime": "PT30H"
}
```

### 5.2. v15.0.0: Activity Tab Real-time Updates

- Comments and updates now load in real-time via WebSocket/SSE
- Emoji reactions added to comments (new `_embedded.reactions` in activity)
- No API changes, but UI behavior differs

### 5.3. v16.0.0: Internal Comments (Enterprise)

**New Permission-based Field**:
```json
// In Activity/Journal entries
{
  "comment": { "raw": "..." },
  "internal": true,  // NEW: Only visible to users with permission
  "_links": {
    "user": { "href": "/api/v3/users/123" }
  }
}
```

### 5.4. v16.0.0: Auto-generated Subjects (Enterprise)

Work packages may have auto-generated subjects based on patterns defined by admins. The `subject` field may become read-only for certain work package types.

### 5.5. HATEOAS Structural Guarantees (API v3)

As of the Jan 2026 audit of OpenProject 17 documentation, the API v3 provides specific structural guarantees:

#### 5.5.1. The Full Embedding Guarantee
- **Rule**: In OpenProject's implementation of HAL+JSON, if a resource is present in the `_embedded` object, it is guaranteed to be the **full representation** (not a partial summary).
- **Client Optimization**: This eliminates the need for "hydration checks" when navigating from a collection to its linked entities, provided they are embedded.

#### 5.5.2. Context-Sensitive Actions
- **Rule**: Links within the `_links` object (like `update`, `delete`, `copy`) are strictly context-sensitive.
- **Usage**: They serve as a real-time permission manifest. If the `update` link is missing, the authenticated user definitively lacks permission.


---

## 6. Authentication Changes

### 6.1. v15.0.0: OIDC/SAML UI Configuration

- Settings-based configuration deprecated
- All providers converted to database-stored UI elements
- Environment variable configuration still works but creates read-only entries

### 6.2. v17.0.0: Built-in OAuth Application

**Major Addition for External Clients**:

OpenProject v17 includes a built-in OAuth application that simplifies authentication for external clients (like mobile apps or our PM Agent).

**Benefits**:
- No manual OAuth configuration required for default use cases
- Immediate availability for secure, user-based authentication
- Especially useful for mobile app integration

**API Discovery**:
```
GET /api/v3/configuration
```

May include new OAuth application details in v17.

---

## 7. Database & Infrastructure Changes

### 7.1. PostgreSQL Version Requirements

| OpenProject Version | PostgreSQL Required |
|---------------------|---------------------|
| v13.x | 13+ |
| v14.x | 13+ |
| v15.x | 13+ |
| v16.x | 13+ |
| v17.x | **17.0 (Mandatory)** |

> **Note**: v17 Docker images and schema migrations REQUIRES PostgreSQL 17.0 (specifically for the `transaction_timeout` parameter). Using older versions like PG 15 will cause migration failures.

### 7.2. v17.0.0: Package Source Change

Package source changed from `dl.packager.io` to `packages.openproject.com`. This affects packaged installations, not Docker.

### 7.3. v17.0.0: Project Selector Optimization (Sharding)

- **Behavior**: The project selector (global) now loads an initial **300 projects** and fetches additional entries dynamically via search/scroll.
- **Impact**: Significantly reduces initial payload size and improves perceived performance in high-density instances.
- **API Impact**: While the UI is faster, backend scraping tools that rely on a full list (e.g., `list_projects`) still face the truncation risk unless pagination or specific name filtering is used at the API level.

---

## 8. Implementation Recommendations

### 8.1. OpenProjectV17Provider Strategy

Given the research, here's the recommended approach for implementing `OpenProjectV17Provider`:

#### Option A: Extend V13 Provider (Recommended)
```python
class OpenProjectV17Provider(OpenProjectV13Provider):
    """
    Extends V13 provider with v17-specific enhancements.
    Core API patterns remain identical.
    """
    
    def _parse_relation(self, data: dict) -> dict:
        # Handle lag instead of delay
        lag = data.get("lag", data.get("delay", 0))
        return {"lag": lag, ...}
    
    def _parse_time_entry(self, data: dict) -> PMTimeEntry:
        entry = super()._parse_time_entry(data)
        # Add v16+ fields
        entry.start_time = data.get("startTime")
        entry.end_time = data.get("endTime")
        return entry
```

#### Option B: Version Detection with Feature Flags
```python
class OpenProjectProvider:
    def __init__(self, base_url: str, api_key: str):
        self.version = self._detect_version()
        self.features = self._get_feature_flags()
    
    def _get_feature_flags(self) -> dict:
        return {
            "use_lag_not_delay": self.version >= (14, 0, 0),
            "exact_time_tracking": self.version >= (16, 0, 0),
            "built_in_oauth": self.version >= (17, 0, 0),
            "realtime_documents": self.version >= (17, 0, 0),
        }
```

### 8.2. Backward Compatibility Checklist

When implementing v17 support, ensure:

- [ ] Relations API uses `lag` instead of `delay`
- [ ] Remove any calls to `available_responsibles` (use `available_assignees`)
- [ ] Parse `startTime`/`endTime` in time entries (optional fields)
- [ ] Handle `internal` flag in comments for Enterprise instances
- [ ] If using OIDC: Ensure tokens include `api_v3` scope
- [ ] Test with PostgreSQL 17.0 compatibility

### 8.3. Testing Strategy

```bash
# Run v13 and v17 side-by-side for comparison
# v13: http://localhost:8083
# v17: http://localhost:8084

# Compare API specs
curl http://localhost:8083/api/v3/spec.json > spec_v13.json
curl http://localhost:8084/api/v3/spec.json > spec_v17.json

# Diff the specs to find new/changed endpoints
diff spec_v13.json spec_v17.json
```

---

## 9. References

- [OpenProject 14.0.0 Release Notes](https://www.openproject.org/docs/release-notes/14-0-0/)
- [OpenProject 15.0.0 Release Notes](https://www.openproject.org/docs/release-notes/15-0-0/)
- [OpenProject 16.0.0 Release Notes](https://www.openproject.org/docs/release-notes/16-0-0/)
- [OpenProject 17.0.0 Release Notes](https://www.openproject.org/docs/release-notes/17-0-0/)
- [OpenProject API Documentation](https://www.openproject.org/docs/api/)
- [OpenProject API Introduction](https://www.openproject.org/docs/api/introduction/)

---

## 10. Appendix: Quick Diff Summary

### API Breaking Changes (v13 → v17)

| Version | Change | Migration Required |
|---------|--------|-------------------|
| v14 | `delay` → `lag` in Relations | Yes - field rename |
| v14 | `available_responsibles` removed | Yes - use `available_assignees` |
| v16 | JWT requires `api_v3` scope | Yes - if using OIDC |

### New Optional Features (Non-Breaking)

| Version | Feature | Notes |
|---------|---------|-------|
| v14 | Progress auto-calculation | Read-only `percentageDone` in Work-based mode |
| v15 | Emoji reactions | New `_embedded.reactions` in activity |
| v16 | Time entry start/end | New `startTime`, `endTime` fields |
| v16 | Internal comments | Enterprise only, new `internal` flag |
| v17 | Documents API | Real-time with Hocuspocus |
| v17 | Enhanced Meetings | Draft mode, outcomes, iCal |
| v17 | Built-in OAuth | Easier external client setup |
