import pandas as pd
import json
import re

# ---- Load your variant → canonical mapping JSON ----
with open("competitor_normalization.json", "r") as f:
    normalization = json.load(f)

variant_to_canonical = normalization["variant_to_canonical"]

def normalize_text(text: str) -> str:
    """
    Preprocess text for matching:
    - lowercase
    - strip spaces/dashes
    - normalize & → 'and'
    """
    if not isinstance(text, str):
        return ""
    txt = text.lower().strip()
    txt = txt.replace("&", "and")
    txt = txt.replace("-", " ")
    txt = " ".join(txt.split())  # collapse spaces
    return txt

def resolve_competitor(raw: str) -> tuple[str, str]:
    """
    Map raw text to canonical competitor name using dictionary.
    Returns (canonical, variant_found).
    """
    norm = normalize_text(raw)
    if norm in variant_to_canonical:
        return variant_to_canonical[norm], norm
    else:
        return "Generic/Unclear", norm

def extract_competitors(text):
    """
    Extract competitor mentions from transcript text.
    Returns a list of found competitor variants.
    """
    # List of competitor keywords to search for in the text
    competitor_variants = list(variant_to_canonical.keys())
    found_competitors = []
    
    # Normalize the text for searching
    normalized_text = normalize_text(text)
    
    # Search for each variant in the text
    for variant in competitor_variants:
        if variant in normalized_text:
            found_competitors.append(variant)
    
    # If no competitors found, return "Generic/Unclear"
    if not found_competitors:
        return ["Generic/Unclear"]
    
    return found_competitors

# ---- Load your source CSV ----
df = pd.read_csv("source.csv")

# ---- Process transcripts to find competitors ----
# Create empty lists to store results
all_competitor_canonicals = []
all_variants_found = []

# Process each transcript
for transcript in df["ConcatenatedText"]:
    found_competitors = extract_competitors(transcript)
    
    # Get unique canonical names and variants
    canonicals = []
    variants = []
    
    for competitor in found_competitors:
        canonical, variant = resolve_competitor(competitor)
        if canonical not in canonicals:
            canonicals.append(canonical)
            variants.append(variant)
    
    # Instead of joining with semicolons, store as list
    all_competitor_canonicals.append(canonicals)
    all_variants_found.append(variants)

# ---- Add results to dataframe ----
# Instead of creating a single column with semicolon-separated values, create multiple columns
competitor_df = pd.DataFrame(all_competitor_canonicals, index=df.index)
competitor_df.columns = [f'competitor_canonical_{i+1}' for i in range(competitor_df.shape[1])]

# Optionally, you can also keep the list column if desired; here we replace it
# df["competitor_canonical"] = all_competitor_canonicals

# Concatenate the new competitor columns with the original dataframe
df = pd.concat([df, competitor_df], axis=1)

# ---- Save updated CSV ----
df.to_csv("source_normalized.csv", index=False)

print("✅ Normalized CSV saved as source_normalized.csv")
