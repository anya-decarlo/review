#!/usr/bin/env python3
"""
Combine Telehealth Measures Results
-----------------------------------
This script combines individual telehealth measure CSV files into a single summary file.

Usage:
    python combine_results.py --input_dir data/llm_analysis --output_file data/telehealth_measures_summary.csv
"""

import os
import argparse
import pandas as pd
import glob

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Combine telehealth measure results')
    parser.add_argument('--input_dir', default='data/llm_analysis',
                        help='Directory containing individual measure CSV files')
    parser.add_argument('--output_file', default='data/telehealth_measures_summary.csv',
                        help='Output file for combined measures')
    return parser.parse_args()

def main():
    """Main function."""
    args = parse_arguments()
    
    # Convert relative paths to absolute paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    input_dir = args.input_dir
    if not os.path.isabs(input_dir):
        input_dir = os.path.join(project_dir, input_dir)
    
    output_file = args.output_file
    if not os.path.isabs(output_file):
        output_file = os.path.join(project_dir, output_file)
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Find all CSV files in the input directory
    csv_files = glob.glob(os.path.join(input_dir, '*_measures.csv'))
    
    if not csv_files:
        print(f"No CSV files found in {input_dir}")
        return
    
    print(f"Found {len(csv_files)} CSV files to combine")
    
    # Combine all CSV files
    dfs = []
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        if not df.empty:
            dfs.append(df)
    
    if not dfs:
        print("No data found in any of the CSV files")
        return
    
    # Combine all dataframes
    combined_df = pd.concat(dfs, ignore_index=True)
    
    # Save combined dataframe
    combined_df.to_csv(output_file, index=False)
    
    # Create a summary by category
    category_summary = combined_df.groupby(['filename', 'category']).size().reset_index(name='count')
    category_summary_file = os.path.splitext(output_file)[0] + '_by_category.csv'
    category_summary.to_csv(category_summary_file, index=False)
    
    # Print summary
    print(f"\nAnalysis complete:")
    print(f"- Found {len(combined_df)} telehealth measures across {len(csv_files)} articles")
    print(f"- Combined measures saved to {output_file}")
    print(f"- Category summary saved to {category_summary_file}")
    
    # Print category counts
    print("\nMeasures by category:")
    category_counts = combined_df['category'].value_counts()
    for category, count in category_counts.items():
        print(f"- {category}: {count}")

if __name__ == "__main__":
    main()
