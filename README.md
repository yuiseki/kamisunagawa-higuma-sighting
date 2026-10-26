# kamisunagawa-higuma-sighting

Reproducible collection of the ヒグマ出没マップ (brown bear sightings, R6 to R8) of Kamisunagawa Town,
Hokkaido, from the BODIK open data catalogue. The dataset card is generated into `data/README.md` (not
tracked; the data is published at https://huggingface.co/datasets/yuiseki/kamisunagawa-higuma-sighting).

```
uv run python scripts/01_download.py      # the three CSVs and the catalogue metadata (data/raw/<date>)
uv run python scripts/02_export_parquet.py
uv run python scripts/03_verify.py        # Parquet vs the CSVs, with a second reader
uv run python scripts/04_card.py
uv run python src/publish.py [--push]     # dry run by default
```

Code: MIT. Data: CC BY 4.0, see the card.
