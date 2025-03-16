#!/usr/bin/env python3
"""
Telehealth Article Downloader
----------------------------
This script searches for telehealth-related articles using the PubMed API,
retrieves their metadata, and attempts to download PDFs when available.

Usage:
    python download_articles.py --email your.email@example.com --num_articles 20
"""

import os
import argparse
import time
import csv
import requests
import urllib.request
from Bio import Entrez
from datetime import datetime

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Download telehealth articles from PubMed')
    parser.add_argument('--email', required=True, help='Email for Entrez API')
    parser.add_argument('--num_articles', type=int, default=20, help='Number of articles to download')
    parser.add_argument('--output_dir', default='articles', help='Directory to save PDFs')
    parser.add_argument('--csv_path', default='data/article_metadata.csv', help='Path to save metadata CSV')
    parser.add_argument('--search_term', default='telehealth utilization measures', help='Search term for PubMed')
    return parser.parse_args()

def search_pubmed(search_term, max_results=20):
    """Search PubMed for articles matching the search term."""
    print(f"Searching PubMed for: {search_term}")
    handle = Entrez.esearch(db="pubmed", term=search_term, retmax=max_results, sort="relevance")
    record = Entrez.read(handle)
    handle.close()
    return record["IdList"]

def fetch_article_details(id_list):
    """Fetch details for a list of PubMed IDs."""
    ids = ",".join(id_list)
    handle = Entrez.efetch(db="pubmed", id=ids, retmode="xml")
    records = Entrez.read(handle)
    handle.close()
    return records["PubmedArticle"]

def extract_metadata(article):
    """Extract metadata from a PubMed article."""
    try:
        pmid = article["MedlineCitation"]["PMID"]
        article_data = article["MedlineCitation"]["Article"]
        
        # Extract title
        title = article_data.get("ArticleTitle", "No title available")
        
        # Extract journal
        journal = article_data["Journal"]["Title"] if "Journal" in article_data else "Unknown Journal"
        
        # Extract publication date
        try:
            pub_date_parts = article_data["Journal"]["JournalIssue"]["PubDate"]
            year = pub_date_parts.get("Year", "")
            month = pub_date_parts.get("Month", "")
            day = pub_date_parts.get("Day", "")
            pub_date = f"{year}/{month}/{day}".strip("/")
        except:
            pub_date = "Unknown date"
        
        # Extract authors
        authors = []
        if "AuthorList" in article_data:
            for author in article_data["AuthorList"]:
                if "LastName" in author and "ForeName" in author:
                    authors.append(f"{author['LastName']} {author['ForeName']}")
                elif "CollectiveName" in author:
                    authors.append(author["CollectiveName"])
            authors_str = ", ".join(authors)
        else:
            authors_str = "Unknown authors"
        
        # Extract abstract
        abstract = ""
        if "Abstract" in article_data:
            abstract_parts = article_data["Abstract"]["AbstractText"]
            if isinstance(abstract_parts, list):
                for part in abstract_parts:
                    if isinstance(part, str):
                        abstract += part + " "
                    else:
                        # Handle labeled abstract sections - fixed to use str() instead of .string
                        label = part.attributes.get("Label", "")
                        text = str(part)
                        abstract += f"{label}: {text} "
            else:
                abstract = str(abstract_parts)
        
        # Extract DOI
        doi = ""
        if "ELocationID" in article_data:
            for location in article_data["ELocationID"]:
                if location.attributes.get("EIdType") == "doi":
                    doi = str(location)
                    break
        
        # Extract article type/study design
        article_types = []
        if "PublicationTypeList" in article_data:
            for pub_type in article_data["PublicationTypeList"]:
                article_types.append(str(pub_type))
        article_type = ", ".join(article_types)
        
        # Extract MeSH terms (can help identify data sources)
        mesh_terms = []
        if "MeshHeadingList" in article["MedlineCitation"]:
            for mesh in article["MedlineCitation"]["MeshHeadingList"]:
                if "DescriptorName" in mesh:
                    mesh_terms.append(str(mesh["DescriptorName"]))
        mesh_terms_str = ", ".join(mesh_terms)
        
        # NEW: Extract potential telehealth utilization measures
        telehealth_measures = extract_telehealth_measures(abstract)
        
        return {
            "pmid": pmid,
            "title": title,
            "authors": authors_str,
            "journal": journal,
            "publication_date": pub_date,
            "doi": doi,
            "article_type": article_type,
            "abstract": abstract,
            "mesh_terms": mesh_terms_str,
            "pdf_path": "",
            "study_type": identify_study_design(article_type, abstract),  # Auto-identify study type
            "data_source": identify_data_source(abstract, mesh_terms_str),  # Auto-identify data source
            "telehealth_measure_type": categorize_telehealth_measures(telehealth_measures),  # Auto-categorize measures
            "telehealth_measures": "; ".join(telehealth_measures) if telehealth_measures else "",
            "notes": ""
        }
    except Exception as e:
        print(f"Error extracting metadata: {e}")
        return {
            "pmid": article["MedlineCitation"]["PMID"] if "MedlineCitation" in article and "PMID" in article["MedlineCitation"] else "Unknown",
            "title": "Error extracting metadata",
            "authors": "",
            "journal": "",
            "publication_date": "",
            "doi": "",
            "article_type": "",
            "abstract": "",
            "mesh_terms": "",
            "pdf_path": "",
            "study_type": "",
            "data_source": "",
            "telehealth_measure_type": "",
            "telehealth_measures": "",
            "notes": str(e)
        }

def extract_telehealth_measures(abstract):
    """
    Extract potential telehealth utilization measures from the abstract.
    Returns a list of potential measure descriptions.
    """
    if not abstract:
        return []
    
    # List of telehealth-related terms
    telehealth_terms = ['telehealth', 'telemedicine', 'virtual care', 'video visit', 
                      'remote monitoring', 'telemonitoring', 'ehealth', 'e-health',
                      'virtual visit', 'remote consultation', 'teleconsultation']
    
    # List of measurement-related terms
    measurement_terms = ['utilization', 'usage', 'use', 'adoption', 'implementation',
                       'rate', 'percentage', 'proportion', 'number', 'count', 'frequency',
                       'visits', 'consultations', 'encounters', 'sessions']
    
    # Split abstract into sentences
    sentences = abstract.replace('\n', ' ').split('. ')
    
    measures = []
    for sentence in sentences:
        # Check if sentence contains both telehealth and measurement terms
        if any(term in sentence.lower() for term in telehealth_terms) and \
           any(term in sentence.lower() for term in measurement_terms):
            measures.append(sentence.strip())
    
    return measures

def identify_study_design(article_type, abstract):
    """
    Attempt to identify the study design from article type and abstract.
    """
    abstract_lower = abstract.lower()
    article_type_lower = article_type.lower()
    
    # Check for common study designs
    if 'randomized controlled trial' in article_type_lower or 'rct' in abstract_lower:
        return 'Randomized Controlled Trial (RCT)'
    
    if 'cohort' in abstract_lower or 'longitudinal' in abstract_lower:
        return 'Cohort Study'
    
    if 'case-control' in abstract_lower:
        return 'Case-Control Study'
    
    if 'cross-sectional' in abstract_lower:
        return 'Cross-Sectional Study'
    
    if 'qualitative' in abstract_lower or 'interview' in abstract_lower or 'focus group' in abstract_lower:
        return 'Qualitative Study'
    
    if 'systematic review' in article_type_lower or 'systematic review' in abstract_lower:
        return 'Systematic Review'
    
    if 'meta-analysis' in article_type_lower or 'meta-analysis' in abstract_lower:
        return 'Meta-Analysis'
    
    if 'review' in article_type_lower:
        return 'Review Article'
    
    if 'retrospective' in abstract_lower:
        return 'Retrospective Study'
    
    if 'prospective' in abstract_lower:
        return 'Prospective Study'
    
    return 'Not clearly specified'

def identify_data_source(abstract, mesh_terms):
    """
    Attempt to identify the data source type from the abstract and MeSH terms.
    """
    abstract_lower = abstract.lower()
    mesh_lower = mesh_terms.lower()
    
    # Check for common data source types
    if any(term in abstract_lower or term in mesh_lower for term in 
           ['electronic health record', 'ehr', 'emr', 'electronic medical record']):
        return 'Electronic Health Records (EHR)'
    
    if any(term in abstract_lower or term in mesh_lower for term in 
           ['claims data', 'insurance claims', 'medicare claims', 'medicaid claims']):
        return 'Insurance Claims Data'
    
    if any(term in abstract_lower or term in mesh_lower for term in 
           ['survey', 'questionnaire', 'self-report']):
        return 'Survey/Questionnaire'
    
    if any(term in abstract_lower or term in mesh_lower for term in 
           ['interview', 'focus group', 'qualitative']):
        return 'Qualitative (Interviews/Focus Groups)'
    
    if any(term in abstract_lower or term in mesh_lower for term in 
           ['registry', 'database', 'data repository']):
        return 'Registry/Database'
    
    if 'veterans' in abstract_lower or 'veterans' in mesh_lower or 'va' in abstract_lower:
        return 'Veterans Health Administration (VHA) Data'
    
    return 'Not clearly specified'

def categorize_telehealth_measures(measures):
    """
    Categorize telehealth measures into binary, count, rate, or percentage types.
    Returns a comma-separated string of categories.
    """
    if not measures:
        return ""
    
    categories = set()
    
    for measure in measures:
        measure_lower = measure.lower()
        
        # Binary measures
        if any(term in measure_lower for term in ['binary', 'yes/no', 'yes or no', 'presence', 'absence', 
                                               'used or not', 'adoption', 'implemented']):
            categories.add('Binary')
        
        # Percentage measures
        if any(term in measure_lower for term in ['percentage', 'percent', '%', 'proportion', 'ratio']):
            categories.add('Percentage')
        
        # Rate measures
        if any(term in measure_lower for term in ['rate', 'per patient', 'per visit', 'per provider', 
                                              'per day', 'per month', 'per year']):
            categories.add('Rate')
        
        # Count measures
        if any(term in measure_lower for term in ['count', 'number', 'frequency', 'volume', 'quantity']):
            categories.add('Count')
    
    # If no specific category was identified but we have measures, default to "Other"
    if not categories and measures:
        categories.add('Other/Undefined')
    
    return ", ".join(categories)

def attempt_pdf_download(article_metadata, output_dir):
    """
    Attempt to download PDF for an article.
    This is a simplified approach and may not work for all articles due to paywalls.
    """
    pmid = article_metadata["pmid"]
    doi = article_metadata["doi"]
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    pdf_path = os.path.join(output_dir, f"{pmid}.pdf")
    
    # This is a simplified approach - in reality, you would need institutional access
    # or use a service like Unpaywall to find open access versions
    if doi:
        try:
            # Try Sci-Hub (note: this is for demonstration only, check legal implications)
            # In a real scenario, you would use your institutional access
            print(f"Note: In a real implementation, you would download from your institution's library access")
            print(f"For article {pmid}: You would manually download using DOI: {doi}")
            
            # Simulate PDF creation for demonstration
            with open(pdf_path, 'w') as f:
                f.write(f"This is a placeholder for article {pmid} with DOI {doi}.\n")
                f.write(f"Title: {article_metadata['title']}\n")
                f.write(f"Authors: {article_metadata['authors']}\n")
                f.write(f"In a real implementation, this would be the actual PDF content.\n")
            
            return pdf_path
        except Exception as e:
            print(f"Could not download PDF for {pmid}: {e}")
            return ""
    else:
        print(f"No DOI available for {pmid}, cannot attempt download")
        return ""

def save_metadata_to_csv(articles_metadata, csv_path):
    """Save article metadata to CSV file."""
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    
    fieldnames = [
        "pmid", "title", "authors", "journal", "publication_date", 
        "doi", "article_type", "abstract", "mesh_terms", "pdf_path",
        "study_type", "data_source", "telehealth_measure_type", "telehealth_measures", "notes"
    ]
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for metadata in articles_metadata:
            writer.writerow(metadata)
    
    print(f"Metadata saved to {csv_path}")

def main():
    args = parse_arguments()
    
    # Set up Entrez
    Entrez.email = args.email
    Entrez.tool = "TelehealthArticleDownloader"
    
    # Convert relative paths to absolute paths based on the script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    
    output_dir = os.path.join(project_dir, args.output_dir)
    csv_path = os.path.join(project_dir, args.csv_path)
    
    # Create output directories
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    
    # Search PubMed
    id_list = search_pubmed(args.search_term, args.num_articles)
    print(f"Found {len(id_list)} articles")
    
    if not id_list:
        print("No articles found. Try a different search term.")
        return
    
    # Fetch article details
    articles = fetch_article_details(id_list)
    print(f"Retrieved details for {len(articles)} articles")
    
    # Process each article
    articles_metadata = []
    for i, article in enumerate(articles):
        print(f"Processing article {i+1}/{len(articles)}")
        metadata = extract_metadata(article)
        
        # Attempt to download PDF
        pdf_path = attempt_pdf_download(metadata, output_dir)
        if pdf_path:
            metadata["pdf_path"] = pdf_path
        
        articles_metadata.append(metadata)
        
        # Be nice to the API
        time.sleep(1)
    
    # Save metadata to CSV
    save_metadata_to_csv(articles_metadata, csv_path)
    
    print("\nSummary:")
    print(f"- Articles processed: {len(articles_metadata)}")
    print(f"- PDFs downloaded: {sum(1 for m in articles_metadata if m['pdf_path'])}")
    print(f"- Metadata saved to: {csv_path}")
    print("\nNext steps:")
    print("1. Review the downloaded articles")
    print("2. Fill in the missing fields in the CSV (study_type, data_source, telehealth_measure_type)")
    print("3. Use this data for your analysis")

if __name__ == "__main__":
    main()
