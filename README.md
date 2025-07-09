# AXIA Evaluation Scripts

This directory contains evaluation scripts for testing AXIA API data extraction performance on different datasets.

## Scripts

### eval_sroie2019.py - Receipt Data Extraction
Evaluates receipt data extraction using the SROIE 2019 dataset.

**Dataset**: SROIE2019 receipt images and expected outputs  
**API Endpoint**: `/api/extract/SROIEReceipt`  
**Evaluators**:
- **CompanyEvaluator**: String similarity matching for company names
- **AddressEvaluator**: String similarity matching for addresses  
- **DateEvaluator**: Binary matching with DD/MM swap handling for dates
- **TotalEvaluator**: Numerical similarity for receipt totals

### eval_handwriting.py - Handwritten Name Extraction
Evaluates handwritten name extraction from the handwriting recognition dataset.

**Dataset**: HANDWRITING images with expected name labels  
**API Endpoint**: `/api/extract/Name`  
**Evaluators**:
- **SimilarityEvaluator**: String similarity matching for extracted names
- **ExactEvaluator**: Binary exact matching for extracted names

## Setup

1. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set the AXIA API key environment variable:
```bash
export AXIA_API_KEY=your_api_key_here
```

4. Ensure datasets are available:
   - SROIE2019: `SROIE2019/cases.yaml` and corresponding image/text files
   - Handwriting: `HANDWRITING/written_name_test_short.csv` and test images

## Running

Run the SROIE 2019 evaluation:
```bash
python -m eval_sroie2019
```

Run the handwriting evaluation:
```bash
python -m eval_handwriting
```

Both scripts support concurrent processing (20 concurrent requests) and provide detailed evaluation reports including input/output comparisons and timing information.

## Features

- **Concurrent Processing**: Both scripts process multiple images simultaneously
- **Robust Date Handling**: SROIE evaluator handles DD/MM swapping in annotations
- **Detailed Reporting**: Comprehensive evaluation reports with timing and comparison data
- **Error Handling**: Graceful handling of API errors and missing data