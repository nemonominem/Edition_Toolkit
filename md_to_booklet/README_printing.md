# Res Gestae Booklet Printing Instructions

## 1. Files produced

- `data/latin.txt`: cleaned Latin text, 35 sections marked with `== SECTION N ==`.
- `build/smallpages/res_gestae_smallpages.pdf`: one 13×21.5 cm page per PDF page, in reading order.
- `build/imposed/res_gestae_imposed_A4.pdf`: A4 duplex-ready imposition spreads (front/back per folio).
- `build/imposed/test_front_folio1.pdf`, `build/imposed/test_back_folio1.pdf`: phase-1/2 test sheets.

## 2. Paper and printer settings

- Paper size: A4 (210 × 297 mm)
- Orientation: landscape for imposition sheets.
- Duplex mode: flip on short edge.
- Print scaling: 100% (no fit-to-page / no shrink-to-fit).

## 3. Cutting and folding (after printing both sides)

1. Trim each A4 sheet to the faint outer crop rectangle (260 × 215 mm). Keep minimal bleed.
2. Score along center fold guide (vertical center of 260 mm content block).
3. Fold each folio in half to 130 × 215 mm.
4. Assemble folios in sheet order: Side A then Side B maps to final reading order.

## 4. Layout references

- Left page (Latin) headers: `Res Gestae · Sect. X`.
- Right page (Translation & Notes) headers: `Res Gestae · Translation & Notes · Sect. X`.
- Outer page numbers at bottom corner.

## 5. Rebuild command

```sh
python scripts/make_booklet.py
```

This regenerates `data/latin.txt`, `build/smallpages/res_gestae_smallpages.pdf`, and `build/imposed/res_gestae_imposed_A4.pdf`.
