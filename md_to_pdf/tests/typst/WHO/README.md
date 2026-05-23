# tests/typst/WHO — WHO article Typst engine outputs

> **Gitignored.** The `.typ` and `.pdf` files here are never committed.
> This directory exists to keep engine outputs separate from source inputs.

## Contents

```
typst/WHO/
├── WHO_Compromission_hardened.typ   Generated Typst source
└── WHO_Compromission_hardened.pdf   Compiled PDF
```

These are produced by running `md2pdf` on the hardened source in
`tests/shared/WHO/` and then moving the outputs here:

```bash
md2pdf md_to_pdf/tests/shared/WHO/WHO_Compromission_hardened.md \
  --style intelligence \
  --meta md_to_pdf/tests/shared/WHO/WHO_Compromission.json \
  --compile

mv md_to_pdf/tests/shared/WHO/WHO_Compromission_hardened.typ \
   md_to_pdf/tests/shared/WHO/WHO_Compromission_hardened.pdf \
   md_to_pdf/tests/typst/WHO/
```

See `tests/shared/WHO/README.md` for the full pipeline (extraction → hardening →
layout tweaks → conversion).
