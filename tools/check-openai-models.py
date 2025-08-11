#!/usr/bin/env python3
"""Check available OpenAI models"""
import os
from openai import OpenAI

# Get API key from environment
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    # Try to read from .env file
    env_file = "/Users/joshuacook/working/radical-symmetry/rs-template/.env"
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if line.startswith("OPENAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    break

if not api_key:
    print("Error: OPENAI_API_KEY not found")
    exit(1)

client = OpenAI(api_key=api_key)

# List available models
print("Available OpenAI Models:")
print("-" * 50)

models = client.models.list()
model_ids = sorted([model.id for model in models.data])

# Filter for GPT models
gpt_models = [m for m in model_ids if "gpt" in m.lower()]

print("\nGPT Models:")
for model in gpt_models:
    print(f"  - {model}")

# Show recommended models
print("\nRecommended for production:")
print("  - gpt-4o (latest, best performance)")
print("  - gpt-4o-mini (cost-effective, fast)")
print("  - gpt-4-turbo (previous generation)")
print("  - gpt-3.5-turbo (legacy, cheapest)")