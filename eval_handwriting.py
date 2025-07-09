from __future__ import annotations

import asyncio
import csv
import logging
import os
from typing import Dict, Any

import aiohttp
from difflib import SequenceMatcher
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


ENDPOINT = "http://localhost:8000/api/extract/Name"
DATASET_CSV_FILE = "HANDWRITING/written_name_test_short.csv"
AXIA_API_KEY = os.environ["AXIA_API_KEY"]

# --- AXIA API ---
# Requests to AXIA is done by making a stanard HTTP POST (POST /extract/SROIEReceipt) as a multipart/form-data request.
# It can handle one image at a time. The image is sent in the `uploaded_file` field.
# The response structure is a JSON object with the output data stored in the `data` field.
# The API Key is provider as a header: `X-API-KEY: <your_api_key>`.

# --- Test Dataset: HANDWRITING ---
# https://www.kaggle.com/datasets/landlord/handwriting-recognition
# Input and Expected output are structured this way:
# HANDWRITING/written_name_test_v2.csv contains the test cases (FILENAME, IDENTITY).
# HANDWRITING/test/*.jpg are the input images.


class NameEvaluator(Evaluator[str, str]):
    """
    Evaluator for comparing handwritten names.
    Uses sequence matching to calculate similarity between extracted and expected names.
    """

    def evaluate(self, ctx: EvaluatorContext) -> float:
        try:
            result = ctx.output['name']
        except KeyError:
            logger.warning(f"Output does not contain 'name' key for case {ctx.inputs}")
            return 0.0
        
        if not result:
            logger.warning(f"Output 'name' is empty for case {ctx.inputs}")
            result = "EMPTY"

        return SequenceMatcher(None, result.upper(), ctx.expected_output['name'].upper()).ratio()


def load_dataset() -> Dataset:
    """Load the handwriting dataset from CSV file."""
    cases = []
    with open(DATASET_CSV_FILE, 'r') as f:
        reader = csv.DictReader(f)

        for case_data in reader:
            case = Case(
                name=case_data["FILENAME"],
                inputs=f"HANDWRITING/test/{case_data['FILENAME']}",
                expected_output={"name": case_data["IDENTITY"]},
                metadata=case_data.get("metadata", {}),
            )
            cases.append(case)

    return Dataset(
        cases=cases,
        evaluators=[
            NameEvaluator(),
        ],
    )

async def extract_name(image_path: str) -> Dict[str, Any]:
    """
    Extracts name data from a handwriting image using the AXIA API.
    
    Args:
        image_path: Path to the image file.
        
    Returns:
        Dictionary containing the extracted name data.
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
    """Main function to run the handwriting evaluation."""
    dataset = load_dataset()
    report = await dataset.evaluate(extract_name, max_concurrency=20)
    report.print(
        include_input=True, 
        include_output=True, 
        include_durations=True, 
        include_expected_output=True
    )


if __name__ == "__main__":
    asyncio.run(main())