#!/usr/bin/env python
"""Download all models specified in settings to cache."""

from transformers import AutoModel

from what_works_repo.settings import settings

for model in settings.ml.pretrained_models:
    print(f"Downloading {model.name}...")
    try:
        AutoModel.from_pretrained(model.name)
        print(f"✓ {model.name}")
    except Exception as e:
        print(f"✗ {model.name}: {e}")

print("Done!")
