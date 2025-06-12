#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pandas as pd

BODYSITE_SNOMED_MAPPING_URL = "https://dicom.nema.org/medical/dicom/current/output/chtml/part16/chapter_L.html"

def download_body_part_mapping(url=BODYSITE_SNOMED_MAPPING_URL):
    print(f"Downloading: {url}")
    dfs = pd.read_html(url, converters={"Code Value": str})
    df = dfs[2][["Code Value", "Code Meaning", "Body Part Examined"]]
    df = df.dropna(subset=["Body Part Examined"])
    return df

def save_json(df, name):
    out_dir = os.path.join("resources", "terminologies")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{name}.json")
    df.to_json(path, orient="records", force_ascii=False)
    print(f"Saved {len(df)} entries to {path}")

def main():
    df_bp = download_body_part_mapping()
    save_json(df_bp, "bodysite_snomed")
    print("All terminologies built.")

if __name__ == "__main__":
    main()