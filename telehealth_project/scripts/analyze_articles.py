#!/usr/bin/env python3
"""
Telehealth Article Analyzer
---------------------------
This script analyzes telehealth articles to extract key metadata including:
- Study type/design
- Data source
- Study population
- Year of study
- Sample size
- Study duration

Usage:
    python analyze_articles.py --pdf_dir articles --output_dir data/individual_articles
"""

import os
import argparse
import pandas as pd
import re
import PyPDF2
from datetime import datetime

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Analyze telehealth articles')
    parser.add_argument('--pdf_dir', default='articles', 
                        help='Directory containing PDF articles')
    parser.add_argument('--output_dir', default='data/individual_articles',
                        help='Directory to save individual article metadata CSV files')
    parser.add_argument('--summary_csv', default='data/article_metadata.csv',
                        help='Path to save the summary of all metadata (optional)')
    return parser.parse_args()

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(len(reader.pages)):
                text += reader.pages[page_num].extract_text()
        return text
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        return ""

def extract_title_from_pdf(text, filename):
    """Extract the title from PDF text."""
    # Look for title in first few lines
    lines = text.split('\n')
    for line in lines[:10]:
        line = line.strip()
        if line and len(line) > 15 and not line.startswith('http'):
            return line
    
    # Fallback to filename
    return os.path.splitext(os.path.basename(filename))[0].replace('_', ' ')

def extract_authors_from_pdf(text):
    """Extract authors from PDF text."""
    # Look for author section
    author_patterns = [
        r'(?i)by\s+([\w\s,\.]+)',
        r'(?i)authors?[:\s]+([\w\s,\.]+)',
        r'(?i)([\w\s,\.]+)\s+Department of',
        r'(?i)([\w\s,\.]+)\s+University'
    ]
    
    for pattern in author_patterns:
        match = re.search(pattern, text[:1000])
        if match:
            return match.group(1).strip()
    
    return "Not extracted"

def extract_publication_year(text):
    """Extract publication year from text."""
    # Look for year patterns in a more controlled way
    # First, look for years in the format (YYYY) which is common for citations
    citation_year = re.search(r'\(\s*?(20\d{2}|19\d{2})\s*?\)', text)
    if citation_year:
        return citation_year.group(1).strip()
    
    # Look for years that are likely to be publication years (between 1990 and current year)
    # This helps avoid extracting random 4-digit numbers
    year_matches = re.findall(r'\b(20\d{2}|19[9][0-9])\b', text[:2000])  # Only look in first 2000 chars
    
    if year_matches:
        # Filter out years that are too far in the future
        current_year = 2025  # As of the knowledge cutoff
        valid_years = [int(y) for y in year_matches if int(y) <= current_year]
        
        if valid_years:
            # Return the most recent valid year that's not in the future
            return str(max(valid_years))
    
    return None

def identify_study_design(text):
    """Identify the study design from text."""
    text_lower = text.lower()
    
    # Define study design patterns with keywords
    study_designs = {
        'Randomized Controlled Trial (RCT)': ['randomized controlled trial', 'rct', 'randomized clinical trial'],
        'Cohort Study': ['cohort study', 'longitudinal study', 'prospective cohort', 'retrospective cohort'],
        'Case-Control Study': ['case-control', 'case control'],
        'Cross-Sectional Study': ['cross-sectional', 'cross sectional'],
        'Qualitative Study': ['qualitative study', 'qualitative research', 'interview study', 'focus group'],
        'Systematic Review': ['systematic review', 'systematic literature review'],
        'Meta-Analysis': ['meta-analysis', 'meta analysis'],
        'Review Article': ['review article', 'literature review', 'narrative review'],
        'Mixed Methods': ['mixed methods', 'mixed-methods'],
        'Quasi-Experimental': ['quasi-experimental', 'quasi experimental', 'non-randomized trial'],
        'Case Series': ['case series', 'case report'],
        'Observational Study': ['observational study', 'observational research'],
        'Pre-Post Study': ['pre-post', 'pre post', 'before and after', 'before-after']
    }
    
    # Check for each study design
    for design, keywords in study_designs.items():
        if any(keyword in text_lower for keyword in keywords):
            return design
    
    # If no specific design found, try to determine if it's a primary or secondary analysis
    if any(term in text_lower for term in ['secondary analysis', 'secondary data', 'retrospective analysis']):
        return 'Secondary Analysis'
    
    if any(term in text_lower for term in ['pilot study', 'pilot trial', 'feasibility study']):
        return 'Pilot/Feasibility Study'
    
    return 'Not clearly specified'

def extract_data_source_type(text):
    """Extract the type of data source used in the study."""
    text_lower = text.lower()
    
    # Define data source patterns with keywords
    data_sources = {
        'Electronic Health Records (EHR)': ['electronic health record', 'ehr', 'electronic medical record', 'emr', 'medical record'],
        'Insurance Claims': ['claims data', 'insurance claims', 'medicare claims', 'medicaid claims', 'billing data'],
        'Survey/Questionnaire': ['survey', 'questionnaire', 'self-report', 'self report', 'patient-reported', 'patient reported'],
        'Interviews/Focus Groups': ['interview', 'focus group', 'qualitative data', 'semi-structured interview'],
        'Registry/Database': ['registry', 'database', 'data repository', 'data warehouse'],
        'Veterans Health Administration (VHA) Data': ['veterans', 'va ', 'veterans health administration', 'vha', 'va health'],
        'Clinical Trial Data': ['clinical trial', 'trial data', 'randomized trial data'],
        'Administrative Data': ['administrative data', 'administrative records'],
        'Social Media Data': ['social media', 'twitter', 'facebook', 'instagram', 'online platform'],
        'Wearable/Sensor Data': ['wearable', 'sensor', 'monitoring device', 'remote monitoring'],
        'Mobile App Data': ['mobile app', 'smartphone app', 'application data', 'app-based']
    }
    
    # Check for each data source
    for source, keywords in data_sources.items():
        if any(keyword in text_lower for keyword in keywords):
            return source
    
    return 'Not clearly specified'

def extract_study_population(text):
    """Extract information about the study population."""
    text_lower = text.lower()
    
    # Define population types with keywords
    population_types = {
        'General Adult Population': ['adult', 'adults', 'general population'],
        'Pediatric/Youth': ['pediatric', 'children', 'adolescent', 'youth', 'child', 'teen'],
        'Elderly': ['elderly', 'older adult', 'geriatric', 'senior', 'aged 65', '65 years and older'],
        'Veterans': ['veteran', 'military', 'service member', 'armed forces'],
        'Rural Population': ['rural', 'remote area', 'underserved area'],
        'Urban Population': ['urban', 'city', 'metropolitan'],
        'Low-Income': ['low income', 'low-income', 'poverty', 'disadvantaged', 'medicaid'],
        'Chronic Disease Patients': ['chronic disease', 'chronic condition', 'chronic illness'],
        'Mental Health Patients': ['mental health', 'psychiatric', 'depression', 'anxiety', 'psychological'],
        'Healthcare Providers': ['provider', 'physician', 'clinician', 'doctor', 'nurse', 'healthcare professional'],
        'Specific Ethnic Groups': ['ethnic', 'racial', 'minority', 'hispanic', 'latino', 'african american', 'black', 'asian'],
        'Pregnant Women': ['pregnant', 'pregnancy', 'maternal', 'prenatal'],
        'COVID-19 Patients': ['covid', 'covid-19', 'coronavirus', 'sars-cov-2', 'pandemic patient']
    }
    
    # Check for each population type
    found_populations = []
    for pop_type, keywords in population_types.items():
        if any(keyword in text_lower for keyword in keywords):
            found_populations.append(pop_type)
    
    if found_populations:
        return ', '.join(found_populations)
    
    return 'Not clearly specified'

def extract_sample_size(text):
    """Extract sample size from text."""
    # Common patterns for reporting sample size
    sample_patterns = [
        r'[nN]\s*=\s*(\d+(?:,\d+)*)',
        r'(?:sample|cohort|population|participants|subjects|patients)\s+(?:size|of)\s+(?:was|were|of)?\s*(?::|was|were)?\s*(\d+(?:,\d+)*)',
        r'(?:included|enrolled|recruited|analyzed)\s+(\d+(?:,\d+)*)\s+(?:patients|participants|subjects|individuals)',
        r'(\d+(?:,\d+)*)\s+(?:patients|participants|subjects|individuals)\s+(?:were|was)\s+(?:included|enrolled|recruited|analyzed)',
        r'data\s+(?:was|were)\s+collected\s+from\s+(\d+(?:,\d+)*)\s+(?:patients|participants|subjects|individuals)'
    ]
    
    for pattern in sample_patterns:
        match = re.search(pattern, text)
        if match:
            # Make sure we're getting a reasonable sample size (not just a single digit that might be a reference)
            sample_size = int(match.group(1).replace(',', ''))
            if sample_size > 10:  # Assuming studies typically have more than 10 participants
                return sample_size
    
    # If no clear sample size found or it's unreasonably small, return None
    return None

def extract_study_duration(text):
    """Extract study duration from text."""
    # Common patterns for study duration
    duration_patterns = [
        r'(?:study|trial|analysis)\s+(?:period|duration)\s+(?:was|of)\s+(\d+)\s+(day|week|month|year)s?',
        r'(?:followed|monitored|tracked)\s+(?:for|over)\s+(?:a\s+period\s+of\s+)?(\d+)\s+(day|week|month|year)s?',
        r'(?:data\s+(?:were|was)\s+collected|study\s+was\s+conducted)\s+(?:over|during|for)\s+(?:a\s+period\s+of\s+)?(\d+)\s+(day|week|month|year)s?',
        r'(\d+)(?:-|\s+to\s+)(\d+)\s+(day|week|month|year)s?\s+(?:study|period|duration)',
        r'between\s+(\w+\s+\d{4})\s+and\s+(\w+\s+\d{4})'  # Date range format
    ]
    
    for pattern in duration_patterns:
        match = re.search(pattern, text)
        if match:
            # Handle different pattern types
            if len(match.groups()) == 2:
                # Simple duration (e.g., "6 months")
                value = match.group(1)
                unit = match.group(2)
                return f"{value} {unit}{'s' if int(value) > 1 and not unit.endswith('s') else ''}"
            elif len(match.groups()) == 3 and match.group(3):
                # Range duration (e.g., "6-12 months")
                start = match.group(1)
                end = match.group(2)
                unit = match.group(3)
                return f"{start}-{end} {unit}{'s' if int(end) > 1 and not unit.endswith('s') else ''}"
            elif len(match.groups()) == 2 and match.group(1) and match.group(2):
                # Date range (e.g., "January 2020 and December 2021")
                start_date = match.group(1)
                end_date = match.group(2)
                return f"{start_date} to {end_date}"
    
    return None

def analyze_pdf_articles(pdf_dir, output_dir, summary_csv=None):
    """
    Analyze PDF articles in the given directory and extract key metadata.
    Save individual CSV files for each article.
    """
    # Check if directory exists
    if not os.path.exists(pdf_dir):
        print(f"Error: PDF directory {pdf_dir} not found.")
        return
    
    # Create output directory if needed
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize results list for summary (if requested)
    results = []
    
    # Get list of PDF files
    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"No PDF files found in {pdf_dir}")
        return
    
    print(f"Found {len(pdf_files)} PDF files to analyze")
    
    # Process each PDF
    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_dir, pdf_file)
        print(f"Processing {pdf_file}...")
        
        # Extract text from PDF
        text = extract_text_from_pdf(pdf_path)
        
        if not text:
            print(f"  Warning: Could not extract text from {pdf_file}")
            continue
        
        # Extract metadata
        title = extract_title_from_pdf(text, pdf_file)
        authors = extract_authors_from_pdf(text)
        publication_year = extract_publication_year(text)
        study_design = identify_study_design(text)
        data_source = extract_data_source_type(text)
        population = extract_study_population(text)
        sample_size = extract_sample_size(text)
        study_duration = extract_study_duration(text)
        
        # Print extracted information
        print(f"  Title: {title}")
        print(f"  Authors: {authors}")
        print(f"  Publication Year: {publication_year}")
        print(f"  Study Design: {study_design}")
        print(f"  Data Source: {data_source}")
        print(f"  Population: {population}")
        print(f"  Sample Size: {sample_size}")
        print(f"  Study Duration: {study_duration}")
        
        # Create article metadata dictionary
        article_data = {
            'filename': pdf_file,
            'title': title,
            'authors': authors,
            'publication_year': publication_year,
            'study_design': study_design,
            'data_source': data_source,
            'population': population,
            'sample_size': sample_size,
            'study_duration': study_duration
        }
        
        # Save individual article metadata to CSV
        article_filename = os.path.splitext(pdf_file)[0]
        article_csv_path = os.path.join(output_dir, f"{article_filename}_metadata.csv")
        article_df = pd.DataFrame([article_data])
        article_df.to_csv(article_csv_path, index=False)
        print(f"  Saved metadata to {article_csv_path}")
        
        # Add to results list for summary if requested
        if summary_csv:
            results.append(article_data)
    
    # Create summary CSV if requested
    if summary_csv and results:
        # Create directory for summary CSV if needed
        os.makedirs(os.path.dirname(summary_csv), exist_ok=True)
        
        # Convert to DataFrame and save
        results_df = pd.DataFrame(results)
        results_df.to_csv(summary_csv, index=False)
        
        # Print summary
        print(f"\nAnalysis complete. Extracted metadata from {len(results)} articles.")
        print(f"Summary saved to {summary_csv}")
        
        # Print study design breakdown
        if not results_df.empty and 'study_design' in results_df.columns:
            design_counts = results_df['study_design'].value_counts()
            print("\nStudy design breakdown:")
            for design, count in design_counts.items():
                print(f"- {design}: {count}")
        
        # Print data source breakdown
        if not results_df.empty and 'data_source' in results_df.columns:
            source_counts = results_df['data_source'].value_counts()
            print("\nData source breakdown:")
            for source, count in source_counts.items():
                print(f"- {source}: {count}")
        
        # Print population breakdown
        if not results_df.empty and 'population' in results_df.columns:
            # This is trickier since populations can be combined
            all_populations = []
            for pop_string in results_df['population'].dropna():
                if pop_string != 'Not clearly specified':
                    all_populations.extend([p.strip() for p in pop_string.split(',')])
            
            if all_populations:
                from collections import Counter
                pop_counts = Counter(all_populations)
                print("\nPopulation breakdown:")
                for pop, count in pop_counts.most_common():
                    print(f"- {pop}: {count}")
    else:
        print(f"\nAnalysis complete. Extracted metadata from {len(pdf_files)} articles.")
        print(f"Individual metadata files saved to {output_dir}")

def main():
    """Main function."""
    args = parse_arguments()
    analyze_pdf_articles(args.pdf_dir, args.output_dir, args.summary_csv)

if __name__ == "__main__":
    main()
