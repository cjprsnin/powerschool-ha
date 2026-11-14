# Brand assets

HACS validation looks for `icon.png` here and/or under `custom_components/powerschool/brand/`.

Generate both locations:

```bash
python3 scripts/install_brand_icons.py
git add brand custom_components/powerschool/brand
git commit -m "Add Marketplace brand icons"
git push origin main
```
