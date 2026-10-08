# RecQ4 Family Depot (prototype)

Static site collecting sequence, structure, alleles, interactions, and literature for RecQ4-family helicases.
Prototype entries: *S. cerevisiae* Hrq1, human RECQL4, *B. subtilis* MrfA.

- `scripts/fetch_data.py` — pulls from UniProt, AlphaFold DB, IntAct, SGD, ClinVar, PubMed into `data/`
- `scripts/build_site.py` — generates all HTML from `data/` (standard library only)
- `.github/workflows/refresh-data.yml` — weekly refresh + rebuild

To add a protein: add an entry (UniProt accession, slug, PubMed query) to `PROTEINS` in `fetch_data.py`, then run both scripts.
