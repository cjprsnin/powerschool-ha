# Changelog

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
