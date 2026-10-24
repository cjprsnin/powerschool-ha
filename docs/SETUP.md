# PowerSchool for Home Assistant — setup notes

## Cards

| Card | Type | Best for |
|------|------|----------|
| **Expandable** | `custom:powerschool-card` | Daily: missing/late, expand for recent work |
| **App (V2)** | `custom:powerschool-v2-card` | Tile grid + class drill-down |

```yaml
type: custom:powerschool-card
student: Trent
scope: current          # current | history | all
recent: 10
show_empty: true
photo: /local/powerschool/trent.jpg
```

## Photos

Desktop guardian portal does **not** expose student photos. Use manual files:

1. Create `config/www/powerschool/`
2. Add `trent.jpg` / `teagan.jpg`
3. Or set `photo: /local/powerschool/trent.jpg` on the card

Cards also try `/local/powerschool/{student_id}.jpg`.

## Term scope

- **School** view: `scope: current`
- **History** view: `scope: history` (empty until prior-term data is tagged)

## HomeKit

Do not expose every course sensor. Prefer only grade averages + missing/late binary sensors. See `examples/homekit-filter.yaml`.

## Resources

Load only one copy of card-mod / mushroom (HACS *or* Linus, not both).
