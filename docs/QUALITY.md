# Quality scale (Silver target)

PowerSchool Grades is a **custom** (Marketplace / HACS) integration. Official Home Assistant **Silver** badges only apply to Core integrations, but we track the same rules so day-to-day behavior matches Silver reliability.

Full rule list: [HA quality scale rules](https://contributors.home-assistant.io/core/quality-scale/rules/).

## Silver checklist (custom)

| Rule | Status |
|------|--------|
| `action-exceptions` | `powerschool.refresh` raises `HomeAssistantError` on failure |
| `config-entry-unloading` | `async_unload_entry` unloads platforms and removes the service |
| `docs-configuration-parameters` | Options documented below |
| `docs-installation-parameters` | Setup fields documented below |
| `entity-unavailable` | Coordinator entities go unavailable when the last update failed |
| `integration-owner` | `codeowners`: `@cjprsnin` |
| `log-when-unavailable` | Logs once when the portal is unreachable, once when it recovers |
| `parallel-updates` | Platforms set `PARALLEL_UPDATES = 0` (coordinator-driven) |
| `reauthentication-flow` | UI reauth when `ConfigEntryAuthFailed` is raised |
| `test-coverage` | Not at Core 95% yet — tracked separately |

## Setup parameters

| Field | Required | Description |
|-------|----------|-------------|
| **District label** | No | Friendly name when multiple districts are linked |
| **PowerSchool URL** | Yes | Base portal URL (`https://district.powerschool.com`) |
| **Username** | Yes | Parent portal username |
| **Password** | Yes | Parent portal password |
| **Update interval** | No | Minutes between scrapes (default **30**, min 5) |
| **Students** | Yes | Multi-select after a successful login |

## Options parameters

| Field | Description |
|-------|-------------|
| **Action** | Save settings, or add another district |
| **Update interval** | Poll frequency in minutes |

Re-authentication: if the password changes or the district locks the account, Home Assistant shows a **Reconfigure** / reauth prompt. You do not need to remove the integration.

## Troubleshooting

| Symptom | What to try |
|---------|-------------|
| Entities unavailable | Check parent portal in a browser; look for `PowerSchool` in the log |
| Reauth prompt | Update password under the integration’s reconfigure flow |
| One district fails, other OK | Multi-district isolates errors; fix the failing district credentials |
| Grades empty for a student | Elementary / standards-only courses may not expose a % |
| Card shows sensor id instead of class name | Update to **1.6.1+** (course attribute + V1/V2 prefer `attributes.course`); hard-refresh card resources |
| Icon missing in Marketplace | Ensure `brand/icon.png` and `custom_components/powerschool/brand/icon.png` are present |

## Removal

**Settings → Devices & services → PowerSchool → Delete.** Optionally remove `config/www/powerschool/` photo cache and any Lovelace cards / automations that reference `sensor.powerschool_*`.

## Demo

Interactive card preview (sample data): [cjprsnin.github.io/powerschool-ha/demo/](https://cjprsnin.github.io/powerschool-ha/demo/)  
Requires GitHub Pages on branch `main`, folder `/docs`.
