import pandas as pd
import json
import re
import os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
from tqdm import tqdm
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---- Load your variant → canonical mapping JSON ----
def load_normalization_mapping():
    """Load the competitor normalization mapping"""
    with open("competitor_normalization.json", "r") as f:
        normalization = json.load(f)
    return normalization["variant_to_canonical"]

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

def resolve_competitor(raw: str, variant_to_canonical: dict) -> tuple[str, str]:
    """
    Map raw text to canonical competitor name using dictionary.
    Returns (canonical, variant_found).
    """
    norm = normalize_text(raw)
    if norm in variant_to_canonical:
        return variant_to_canonical[norm], norm
    else:
        return "Generic/Unclear", norm

def extract_competitors(text, variant_to_canonical: dict):
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

def process_single_row(row_data: tuple) -> tuple:
    """Process a single row of transcript data"""
    idx, transcript, variant_to_canonical = row_data
    
    if pd.isna(transcript) or transcript == "":
        return idx, ["Generic/Unclear"], ["generic/unclear"]
    
    found_competitors = extract_competitors(transcript, variant_to_canonical)
    
    # Get unique canonical names and variants
    canonicals = []
    variants = []
    seen_canonicals = set()
    
    for competitor in found_competitors:
        canonical, variant = resolve_competitor(competitor, variant_to_canonical)
        if canonical not in seen_canonicals:
            canonicals.append(canonical)
            variants.append(variant)
            seen_canonicals.add(canonical)
    
    return idx, canonicals, variants

def process_csv_file(file_path: str, variant_to_canonical: dict) -> str:
    """Process a single CSV file and save the normalized version"""
    logger.info(f"Processing {file_path}")
    
    try:
        # Load the CSV file
        df = pd.read_csv(file_path)
        logger.info(f"Loaded {len(df)} rows from {os.path.basename(file_path)}")
        
        # Check if ConcatenatedText column exists
        if 'ConcatenatedText' not in df.columns:
            logger.warning(f"'ConcatenatedText' column not found in {file_path}. Skipping...")
            return f"Skipped {file_path} - missing ConcatenatedText column"
        
        # Prepare data for parallel processing
        row_data = [(idx, row['ConcatenatedText'], variant_to_canonical) 
                    for idx, row in df.iterrows()]
        
        # Process rows in parallel using ThreadPoolExecutor (better for I/O bound tasks)
        all_competitor_canonicals = [None] * len(df)
        all_variants_found = [None] * len(df)
        
        # Use multiprocessing for CPU-bound text processing
        with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            futures = {executor.submit(process_single_row, data): data[0] 
                      for data in row_data}
            
            # Process completed futures
            for future in tqdm(as_completed(futures), total=len(futures), 
                             desc=f"Processing {os.path.basename(file_path)}"):
                idx, canonicals, variants = future.result()
                all_competitor_canonicals[idx] = canonicals
                all_variants_found[idx] = variants
        
        # Find the maximum number of competitors in any row
        max_competitors = max(len(comps) for comps in all_competitor_canonicals)
        
        # Create competitor columns
        competitor_columns = {}
        for i in range(max_competitors):
            col_name = f'competitor_canonical_{i+1}'
            competitor_columns[col_name] = [
                comps[i] if i < len(comps) else None 
                for comps in all_competitor_canonicals
            ]
        
        # Add columns to dataframe
        for col_name, col_data in competitor_columns.items():
            df[col_name] = col_data
        
        # Also add a column with all competitors as a list (for convenience)
        df['all_competitors'] = [';'.join(comps) for comps in all_competitor_canonicals]
        df['all_variants_found'] = [';'.join(vars) for vars in all_variants_found]
        
        # Save the normalized file
        output_path = file_path.replace('.csv', '_normalized.csv')
        df.to_csv(output_path, index=False)
        
        logger.info(f"✅ Saved normalized file: {output_path}")
        return f"Successfully processed {file_path}"
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        return f"Error processing {file_path}: {str(e)}"

def main():
    """Main function to process all CSV files in the transcripts folder"""
    # Define the transcripts folder path
    transcripts_folder = Path("transcripts")
    
    if not transcripts_folder.exists():
        logger.error("Transcripts folder not found!")
        return
    
    # Load the normalization mapping once
    try:
        variant_to_canonical = load_normalization_mapping()
        logger.info(f"Loaded {len(variant_to_canonical)} competitor variants")
    except Exception as e:
        logger.error(f"Error loading competitor normalization mapping: {e}")
        return
    
    # Find all CSV files in the transcripts folder
    csv_files = list(transcripts_folder.glob("*.csv"))
    
    if not csv_files:
        logger.warning("No CSV files found in the transcripts folder")
        return
    
    logger.info(f"Found {len(csv_files)} CSV files to process")
    
    # Process files sequentially (since each file is processed in parallel internally)
    # This avoids overwhelming the system with too many concurrent processes
    results = []
    for csv_file in csv_files:
        result = process_csv_file(str(csv_file), variant_to_canonical)
        results.append(result)
    
    # Print summary
    logger.info("\n" + "="*50)
    logger.info("PROCESSING COMPLETE")
    logger.info("="*50)
    for result in results:
        logger.info(result)

if __name__ == "__main__":
    main()