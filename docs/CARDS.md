# PowerSchool Lovelace cards

Three custom card variants ship in [`www/`](../www/).

| Card | Type | Style | Best for |
|------|------|--------|----------|
| **V1** | `custom:powerschool-card` | Expandable course list | Desktop detail, history scope |
| **V2** | `custom:powerschool-v2-card` | App-style color tiles + drill-down | Phone / daily check-in |
| **V3** | `custom:powerschool-v3-card` | Class Overview (standalone) | Side-by-side student overview |

Resources (Dashboard → Resources), or via HACS after install:

```text
https://cdn.jsdelivr.net/gh/cjprsnin/powerschool-ha@main/www/powerschool-card.js
https://cdn.jsdelivr.net/gh/cjprsnin/powerschool-ha@main/www/powerschool-v2-card.js
https://cdn.jsdelivr.net/gh/cjprsnin/powerschool-ha@main/www/powerschool-v3-card.js
```

V3 is a **full standalone** card (same UI style as V2). V1/V2/V3 can load independently.

---

## Previews

### V1 — Expandable list

![V1 card](https://cdn.jsdelivr.net/gh/cjprsnin/powerschool-ha@main/docs/images/card-v1.svg)

- Header with student, refresh, average / missing / late stats
- Course rows; tap to expand recent assignments & category detail
- Options: `student`, `scope` (`current` | `history` | `all`), `recent`, `show_empty`

```yaml
type: custom:powerschool-card
student: Trent
scope: current
recent: 10
```

### V2 — App tiles

![V2 card](https://cdn.jsdelivr.net/gh/cjprsnin/powerschool-ha@main/docs/images/card-v2.svg)

- Color-coded grade tiles (subject palette)
- Tap tile → course hero + assignment list
- Assignments tabs: Upcoming / Recent / Status
- Built-in 14-day grade sparklines on course view

```yaml
type: custom:powerschool-v2-card
student: Trent
```

### V3 — Class Overview

![V3 card](https://cdn.jsdelivr.net/gh/cjprsnin/powerschool-ha@main/docs/images/card-v3.svg)

- Class Overview layout: denser grade grid + Missing and Late panel
- Registered as `powerschool-v3-card` for overview dashboards

```yaml
type: custom:powerschool-v3-card
student: Teagan
```

---

## Minimal dashboard (both students)

```yaml
title: School
views:
  - title: Overview
    path: overview
    type: sections
    max_columns: 2
    sections:
      - type: grid
        cards:
          - type: heading
            heading: Trent
            icon: mdi:account-school
          - type: custom:powerschool-v2-card
            student: Trent
            grid_options:
              columns: full
      - type: grid
        cards:
          - type: heading
            heading: Teagan
            icon: mdi:account-school-outline
          - type: custom:powerschool-v3-card
            student: Teagan
            grid_options:
              columns: full
```

More YAML: [`examples/lovelace-cards.yaml`](../examples/lovelace-cards.yaml), [`examples/lovelace-cards-v1-v2-v3.yaml`](../examples/lovelace-cards-v1-v2-v3.yaml), [`examples/school-v2-dashboard.yaml`](../examples/school-v2-dashboard.yaml).

---

## Comparison

| Feature | V1 | V2 / V3 |
|---------|----|--------|
| Expandable courses | Yes | Drill-down pages |
| Color grade tiles | No | Yes |
| Assignment tabs | In expand | Upcoming / Recent / Status |
| Sparklines (14d) | Optional | Built-in |
| `scope` history | Yes | Current-focused |
| Refresh button | Yes | Yes |

---

*Mockups are illustrative (sample grades). Live data comes from the PowerSchool integration sensors.*
