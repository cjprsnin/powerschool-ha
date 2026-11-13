# PowerSchool Lovelace cards

Custom card variants ship in [`www/`](../www/).

| Card | Type | Style | Best for |
|------|------|--------|----------|
| **V1** | `custom:powerschool-card` | Expandable course list | Desktop detail, term scope |
| **V2** | `custom:powerschool-v2-card` | App-style color tiles + drill-down | Phone / daily check-in |
| **V3** | `custom:powerschool-v3-card` | Class overview grid | Side-by-side overview |
| **V4** | `custom:powerschool-v4-card` | Due soon + grades + roster/attendance | Family wall / daily school page |

## Resources

Dashboard → **Resources** → Add (type **JavaScript Module**):

```text
https://cdn.jsdelivr.net/gh/cjprsnin/powerschool-ha@main/www/powerschool-card.js
https://cdn.jsdelivr.net/gh/cjprsnin/powerschool-ha@main/www/powerschool-v2-card.js
https://cdn.jsdelivr.net/gh/cjprsnin/powerschool-ha@main/www/powerschool-v3-card.js
https://cdn.jsdelivr.net/gh/cjprsnin/powerschool-ha@main/www/powerschool-v4-card.js
```

Pin a commit SHA in the URL if you need a fixed revision (cache-bust after updates).

---

## V4 — Due soon + grades (recommended)

Dark mockup-style card:

- **Stats bar:** Average · Classes (tap → roster) · Missing/Late (tap → list) · Attendance (tap → absences/tardies)
- **Due soon** chips (ungraded shown as — / Ungraded, not F)
- **Subject grade** tiles; tap for assignments
- Options: `student` (required), `show_empty` (keep courses with no % yet), `sort: grade`

```yaml
type: custom:powerschool-v4-card
student: Trent
```

```yaml
type: custom:powerschool-v4-card
student: Teagan
show_empty: true
```

School V2 example: [`examples/school-v2-dashboard.yaml`](../examples/school-v2-dashboard.yaml)

---

## V1 — Expandable list

![V1 card](https://cdn.jsdelivr.net/gh/cjprsnin/powerschool-ha@main/docs/images/card-v1.svg)

- Header with student, refresh, average / missing / late
- Course rows; expand for assignments
- Options: `student`, `scope` (`current` | `history` | `all`), `recent`, `show_empty`

```yaml
type: custom:powerschool-card
student: Trent
scope: current
recent: 10
```

## V2 — App tiles

![V2 card](https://cdn.jsdelivr.net/gh/cjprsnin/powerschool-ha@main/docs/images/card-v2.svg)

- Color-coded grade tiles
- Tap tile → course hero + assignment list
- Optional 14-day grade sparklines

```yaml
type: custom:powerschool-v2-card
student: Trent
```

## V3 — Class overview

![V3 card](https://cdn.jsdelivr.net/gh/cjprsnin/powerschool-ha@main/docs/images/card-v3.svg)

- Denser grade grid + missing/late panel

```yaml
type: custom:powerschool-v3-card
student: Teagan
```

---

## Comparison

| Feature | V1 | V2 | V3 | V4 |
|---------|----|----|----|-----|
| Expandable courses | ✓ | | | |
| Color grade tiles | | ✓ | ✓ | ✓ |
| Due soon strip | | | | ✓ |
| Roster / attendance drill | | | | ✓ |
| Term scope option | ✓ | | | |

More YAML: [`examples/lovelace-cards-v1-v2-v3.yaml`](../examples/lovelace-cards-v1-v2-v3.yaml), [`examples/lovelace-v4.yaml`](../examples/lovelace-v4.yaml).
