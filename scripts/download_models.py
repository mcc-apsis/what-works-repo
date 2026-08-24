from transformers import pipeline

from what_works_repo.settings import settings

for model in settings.ml.pretrained_models:
    print(f"Downloading {model.name}...")
    try:
        pipeline(
            "text-classification", model=model.name
        )  # Downloads model + tokenizer + config
        print(f"✓ {model.name}")
    except Exception as e:
        print(f"✗ {model.name}: {e}")
