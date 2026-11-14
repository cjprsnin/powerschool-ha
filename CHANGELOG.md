# Changelog

## 1.5.1 — 2026-11-13

### Added
- **Store cache** for last successful scrape + grade history (entities available before first network poll)
- **Per-district error isolation** (one portal failing does not drop the other)
- **`ConfigEntryAuthFailed`** on login failure (HA reconfigure prompt)
- Thread-local / session-bind path for safer concurrent scrapes (patch scripts)
- Batch multi-section assignment lookup (patch script)
- Photo-miss cache (7-day `.none` marker) and lower default inter-request DELAY (patch scripts)

### Fixed
- Recorder warnings for large course attributes (`_unrecorded_attributes` on assignment/attendance blobs)

### Changed
- Default update interval **30** minutes
- Entity naming via `_attr_has_entity_name` (names relative to student device)
- Diagnostic summary sensors **disabled by default** for new entities
- Notification blueprints: reliable template variables, quieter messages, combined missing/late totals, quiet hours docs
- README Notifications section with import URLs and setup tips

## 1.5.0 — 2026-11-13

### Added
- **Multi-district** support in a single config entry (Add another district in setup / options)
- Optional district **name** label for clearer titles when multiple portals are configured
- **V4 Lovelace card** (`custom:powerschool-v4-card`): due-soon strip, subject grade tiles, tappable Classes → roster, Missing/Late list, Attendance summary
- Config entry **migration** to version 2 (`districts` list) with `async_migrate_entry`
- Schedule / bulletin parsers with junk-header filtering
- Grade history scrape support and photo cache skip when file already exists

### Fixed
- Options flow 500 on Home Assistant 2026.x (do not assign `config_entry` in OptionsFlow `__init__`)
- V4 card grades not showing (course `%` lives in entity `state`, not only `grade_percent` attribute)
- HACS icon/logo packaging for repository branding

### Changed
- Background first refresh so integration setup does not block HA startup
- README and card docs updated for V4 and multi-district

## 1.4.0

- Summary sensors, course sensors, binary sensors
- V1 / V2 / V3 Lovelace cards
- Student photos, refresh service, notification blueprints
