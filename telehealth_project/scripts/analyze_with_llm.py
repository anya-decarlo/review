#!/usr/bin/env python3
"""
Telehealth Article Analyzer with LLM
-----------------------------------
This script enhances telehealth utilization measure extraction using an LLM (OpenAI API).
It processes PDF articles, extracts text, and uses AI to identify and categorize telehealth measures.

Usage:
    # Process a single article:
    python analyze_with_llm.py --single_file articles/AJSLP-30-503.pdf --output_dir data/llm_analysis
"""

import os
import argparse
import json
import pandas as pd
import re
import time
from datetime import datetime
import logging
import openai
import PyPDF2
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("telehealth_analysis.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Default OpenAI API key - Replace this with your actual API key
DEFAULT_API_KEY = "YOUR API KEY"

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Analyze telehealth articles using LLM')
    parser.add_argument('--single_file', required=True,
                        help='Path to a single PDF file to analyze')
    parser.add_argument('--output_dir', default='data/llm_analysis',
                        help='Directory to save the extracted measures')
    parser.add_argument('--api_key', default=DEFAULT_API_KEY,
                        help='OpenAI API key (can also be set via OPENAI_API_KEY environment variable)')
    parser.add_argument('--model', default='gpt-3.5-turbo',
                        help='OpenAI model to use')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode with more verbose output')
    return parser.parse_args()

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(len(reader.pages)):
                try:
                    page_text = reader.pages[page_num].extract_text()
                    if page_text:
                        text += page_text + "\n\n"
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num}: {e}")
        return text
    except Exception as e:
        logger.error(f"Error extracting text from {pdf_path}: {e}")
        return ""

def analyze_with_llm(text_chunk, api_key, model="gpt-3.5-turbo", debug=False):
    """
    Use OpenAI's API to analyze a chunk of text for telehealth measures.
    """
    if debug:
        logger.info(f"Analyzing text chunk of length {len(text_chunk)} with model {model}")
        
    # Create a simpler prompt
    prompt = f"""
    Analyze the following text from a telehealth research article and extract any telehealth utilization measures mentioned.
    
    Telehealth utilization measures are metrics that quantify how telehealth is being used, such as:
    - Whether telehealth was used (yes/no)
    - Number of telehealth visits
    - Rate of telehealth usage
    - Percentage of visits conducted via telehealth
    
    Text: {text_chunk}
    
    Format your response as JSON with the following structure:
    {{
        "measures": [
            {{
                "description": "Description of the measure",
                "category": "Binary/Count/Rate/Percentage/Clinical",
                "value": "Any numeric value mentioned"
            }}
        ]
    }}
    
    If no measures are found, return an empty array for "measures".
    """
    
    try:
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a healthcare research assistant specializing in telehealth."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1000
        )
        
        result = response.choices[0].message.content
        if debug:
            logger.info(f"API response: {result}")
            
        try:
            parsed_result = json.loads(result)
            return parsed_result
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {e}")
            logger.error(f"Raw response: {result}")
            return {"measures": []}
            
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        return {"measures": []}

def analyze_pdf(pdf_path, api_key, model="gpt-3.5-turbo", debug=False):
    """Analyze a PDF file using the LLM."""
    # Extract text from PDF
    logger.info(f"Extracting text from {pdf_path}")
    text = extract_text_from_pdf(pdf_path)
    
    if not text:
        logger.error(f"Could not extract text from {pdf_path}")
        return {"filename": os.path.basename(pdf_path), "measures": []}
    
    if debug:
        logger.info(f"Extracted {len(text)} characters from {pdf_path}")
        
    # For simplicity, just analyze the first 4000 characters
    # This avoids memory issues and keeps costs down
    text_to_analyze = text[:4000]
    
    # Analyze with LLM
    logger.info(f"Analyzing text with {model}")
    result = analyze_with_llm(text_to_analyze, api_key, model, debug)
    
    # Add filename to result
    result["filename"] = os.path.basename(pdf_path)
    
    return result

def save_result(result, output_dir):
    """Save a single result to a JSON file."""
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Save as JSON
    filename = result["filename"]
    base_name = os.path.splitext(filename)[0]
    json_path = os.path.join(output_dir, f"{base_name}_measures.json")
    
    with open(json_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    # Save as CSV
    csv_path = os.path.join(output_dir, f"{base_name}_measures.csv")
    
    if result["measures"]:
        measures_df = pd.DataFrame(result["measures"])
        measures_df["filename"] = filename
        measures_df.to_csv(csv_path, index=False)
    else:
        # Create empty CSV with headers
        pd.DataFrame(columns=["description", "category", "value", "filename"]).to_csv(csv_path, index=False)
    
    return {
        "json_path": json_path,
        "csv_path": csv_path,
        "measure_count": len(result["measures"])
    }

def main():
    """Main function."""
    args = parse_arguments()
    
    # Get API key from command line, environment variable, or default
    api_key = args.api_key or os.environ.get('OPENAI_API_KEY') or DEFAULT_API_KEY
    if api_key == "your_openai_api_key_here":
        logger.error("Please replace the default API key in the script with your actual OpenAI API key")
        return
    
    # Process the file
    pdf_path = args.single_file
    if not os.path.isabs(pdf_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(script_dir)
        pdf_path = os.path.join(project_dir, pdf_path)
    
    output_dir = args.output_dir
    if not os.path.isabs(output_dir):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(script_dir)
        output_dir = os.path.join(project_dir, output_dir)
    
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file {pdf_path} not found.")
        return
    
    # Enable debug mode if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    # Analyze the PDF
    logger.info(f"Processing file: {pdf_path}")
    try:
        result = analyze_pdf(pdf_path, api_key, args.model, args.debug)
        
        # Save the result
        if result:
            output = save_result(result, output_dir)
            logger.info(f"Analysis complete. Found {output['measure_count']} telehealth measures.")
            logger.info(f"Results saved to {output['json_path']} and {output['csv_path']}")
            
            print(f"\nAnalysis complete for {os.path.basename(pdf_path)}")
            print(f"Found {output['measure_count']} telehealth measures")
            print(f"Results saved to:")
            print(f"  - JSON: {output['json_path']}")
            print(f"  - CSV: {output['csv_path']}")
        else:
            logger.error(f"Failed to analyze {pdf_path}")
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
