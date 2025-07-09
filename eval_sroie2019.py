from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Dict, Any

import aiohttp
import yaml
from dateutil import parser
from difflib import SequenceMatcher
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


ENDPOINT = "http://localhost:8000/api/extract/SROIEReceipt"
DATASET_YAML_FILE = "SROIE2019/cases.yaml"
AXIA_API_KEY = os.environ["AXIA_API_KEY"]

# --- AXIA API ---
# Requests to AXIA is done by making a stanard HTTP POST (POST /extract/SROIEReceipt) as a multipart/form-data request.
# It can handle one image at a time. The image is sent in the `uploaded_file` field.
# The response structure is a JSON object with the output data stored in the `data` field.
# The API Key is provider as a header: `X-API-KEY: <your_api_key>`.

# --- Test Dataset: SROIE 2019 ---
# Input and Expected output are structured this way:
# SROIE2019/test/img/*.jpg are the input images.
# SROIE2019/test/entities/*.txt are the expected outputs. The contents are in JSON.
# The filenames of the input images and expected outputs match (eg. X00016469670.jpg -> X00016469670.txt).


class CompanyEvaluator(Evaluator[str, str]):
    """
    Evaluator for comparing company names from receipts.
    Uses sequence matching to calculate similarity between extracted and expected company names.
    """

    def evaluate(self, ctx: EvaluatorContext) -> float:
        if ctx.output.get('company') is None or ctx.expected_output.get('company') is None:
            logger.warning(f"Missing company key for case {ctx.inputs}")
            return 0.0

        return SequenceMatcher(None, ctx.output['company'].upper(), ctx.expected_output['company'].upper()).ratio()


class AddressEvaluator(Evaluator[str, str]):
    """
    Evaluator for comparing addresses from receipts.
    Uses sequence matching to calculate similarity between extracted and expected addresses.
    """

    def evaluate(self, ctx: EvaluatorContext) -> float:
        if ctx.output.get('address') is None or ctx.expected_output.get('address') is None:
            logger.warning(f"Missing address key for case {ctx.inputs}")
            return 0.0

        return SequenceMatcher(None, ctx.output['address'].upper(), ctx.expected_output['address'].upper()).ratio()


class DateEvaluator(Evaluator[str, str]):
    """
    Evaluator for comparing dates from receipts.
    Handles DD/MM swapping in dirty annotations with binary matching.
    """

    def _swap_day_month(self, date_str: str) -> str:
        """Generate DD/MM swapped version of a date string in YYYY-MM-DD format."""
        try:
            year, month, day = date_str.split('-')
            return f"{year}-{day}-{month}"
        except (ValueError, IndexError):
            return date_str

    def evaluate(self, ctx: EvaluatorContext) -> float:
        if ctx.output.get('date') is None or ctx.expected_output.get('date') is None:
            logger.warning(f"Missing date key for case {ctx.inputs}")
            return 0.0

        try:
            # Parse expected date to normalized format
            expected_date_obj = parser.parse(ctx.expected_output['date'])
            expected_date = expected_date_obj.strftime('%Y-%m-%d')
            
            # Generate DD/MM swapped version
            expected_date_swapped = self._swap_day_month(expected_date)
            
            # Parse output date to normalized format
            output_date_obj = parser.parse(ctx.output['date'])
            output_date = output_date_obj.strftime('%Y-%m-%d')
            
            # Binary matching: 1.0 for exact match (original or swapped), 0.0 otherwise
            if output_date == expected_date or output_date == expected_date_swapped:
                return 1.0
            else:
                return 0.0
                
        except (ValueError, TypeError) as e:
            logger.warning(f"Date parsing error for case {ctx.inputs}: {e}")
            return 0.0


class TotalEvaluator(Evaluator[str, str]):
    """
    Evaluator for comparing receipt total amounts.
    Handles currency formatting and calculates similarity scores for numeric totals.
    """

    def _clean_total(self, total_str: str) -> float:
        """Clean and parse a total string to float."""
        try:
            # Remove currency symbols and commas, then convert to float
            cleaned = total_str.replace('$', '').replace(',', '').replace('RM', '').strip()
            return float(cleaned)
        except (ValueError, AttributeError):
            return 0.0

    def evaluate(self, ctx: EvaluatorContext) -> float:
        if ctx.output.get('total') is None or ctx.expected_output.get('total') is None:
            logger.warning(f"Missing total key for case {ctx.inputs}")
            return 0.0

        expected_total = self._clean_total(ctx.expected_output['total'])
        if expected_total == 0:
            logger.warning(f"Invalid expected total: {ctx.expected_output['total']}")
            return 0.0

        try:
            output_total = float(ctx.output['total'])
        except (ValueError, TypeError):
            logger.warning(f"Invalid output total: {ctx.output['total']}")
            return 0.0

        # Exact match
        if expected_total == output_total:
            return 1.0

        # Similarity score based on relative difference
        score = 1 - abs(expected_total - output_total) / expected_total
        return max(0.0, score)

#
def load_dataset() -> Dataset:
    """Load the SROIE 2019 dataset from YAML configuration."""
    with open(DATASET_YAML_FILE) as f:
        dataset_data = yaml.safe_load(f)

    cases = []
    for case_data in dataset_data["cases"]:
        # Load the expected output from the JSON in the text file
        expected_output_file = case_data["expected_output"]
        with open(expected_output_file, "r") as f:
            expected_output = json.load(f)
        case = Case(
            name=case_data["name"],
            inputs=case_data["inputs"],
            expected_output=expected_output,
            metadata=case_data.get("metadata", {}),
        )
        cases.append(case)

    return Dataset(
        cases=cases,
        evaluators=[
            CompanyEvaluator(),
            AddressEvaluator(),
            DateEvaluator(),
            TotalEvaluator(),
        ],
    )



async def extract_receipt(image_path: str) -> Dict[str, Any]:
    """
    Extracts receipt data from an image using the AXIA API.
    
    Args:
        image_path: Path to the image file.
        
    Returns:
        Dictionary containing the extracted receipt data.
    """
    async with aiohttp.ClientSession() as session:
        with open(image_path, "rb") as image_file:
            async with session.post(
                ENDPOINT,
                headers={"X-API-KEY": AXIA_API_KEY},
                data={"uploaded_file": image_file},
            ) as response:
                try:
                    res = await response.json()
                    return res.get('data', {})
                except Exception as e:
                    logger.error(f"Error processing response: {e}")
                    return {"error": "Unable to parse"}
            

async def main() -> None:
    """Main function to run the evaluation."""
    dataset = load_dataset()
    report = await dataset.evaluate(extract_receipt, max_concurrency=20)
    report.print(
        include_input=True, 
        include_output=True, 
        include_durations=True, 
        include_expected_output=True
    )


if __name__ == "__main__":
    asyncio.run(main())