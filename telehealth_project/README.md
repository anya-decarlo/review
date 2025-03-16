# MiniTelehealth Research Project

This project demonstrates telehealth utilization measure analysis capabilities by downloading relevant articles and extracting key data points. It was created as a sample project for a Temporary Research Assistant application at the Veterans Health Administration.

## Project Structure

```
telehealth_project/
├── articles/       # Downloaded article PDFs
├── data/           # CSV files with article metadata and analysis
├── scripts/        # Python scripts for downloading and analyzing articles
└── requirements.txt # Required Python packages
```

## Setup

1. Install required packages:
   ```
   pip install -r requirements.txt
   ```

2. Create a Python virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

## Usage

### 1. Download Articles

The `download_articles.py` script searches PubMed for telehealth-related articles and attempts to download PDFs when available.

```
python scripts/download_articles.py --email your.email@example.com --num_articles 20
```

Parameters:
- `--email`: Your email (required for PubMed API)
- `--num_articles`: Number of articles to download (default: 20)
- `--output_dir`: Directory to save PDFs (default: ../articles)
- `--csv_path`: Path to save metadata CSV (default: ../data/article_metadata.csv)
- `--search_term`: Search term for PubMed (default: "telehealth utilization measures")

### 2. Analyze Articles

The `analyze_articles.py` script extracts and categorizes telehealth utilization measures from the downloaded articles.

```
python scripts/analyze_articles.py --csv_path data/article_metadata.csv
```

Parameters:
- `--csv_path`: Path to the article metadata CSV (default: ../data/article_metadata.csv)
- `--output_csv`: Path to save the extracted measures (default: ../data/telehealth_measures.csv)

### 3. Enhanced Analysis with LLM

The `analyze_with_llm.py` script uses OpenAI's API to perform more sophisticated analysis of telehealth measures in the articles.

```
python scripts/analyze_with_llm.py --pdf_dir articles --output_dir data/llm_analysis --api_key YOUR_OPENAI_API_KEY
```

Parameters:
- `--pdf_dir`: Directory containing PDF articles (default: articles)
- `--output_dir`: Directory to save the extracted measures (default: data/llm_analysis)
- `--api_key`: OpenAI API key (required)
- `--chunk_size`: Size of text chunks to send to the LLM (default: 4000)
- `--model`: OpenAI model to use (default: gpt-4-turbo)

Benefits of LLM-enhanced analysis:
- More accurate categorization of telehealth measures
- Better extraction of context and clinical significance
- Improved handling of complex medical terminology
- More consistent results across different article formats

## Telehealth Utilization Measure Categories

This project categorizes telehealth utilization measures into four main types:

1. **Binary measures**: Yes/no indicators of telehealth use (e.g., whether a patient used telehealth)
2. **Count measures**: Absolute numbers (e.g., number of telehealth visits)
3. **Rate measures**: Measures per unit time/population (e.g., telehealth visits per patient per year)
4. **Percentage measures**: Proportions (e.g., percentage of all visits conducted via telehealth)

## Notes for Real Implementation

In a real implementation with institutional access:
1. The PDF download functionality would use your institution's library access
2. You would manually download PDFs that cannot be automatically retrieved
3. You would review and refine the automatically extracted data

## License

This project is for demonstration purposes only.
