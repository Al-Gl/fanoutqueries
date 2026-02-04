import pandas as pd
from unittest.mock import MagicMock
import sys
import os

# Mock the genai module before importing fan_out_logic
sys.modules["google.generativeai"] = MagicMock()
import fan_out_logic

def test_pipeline():
    print("Testing CSV Loading...")
    try:
        df = pd.read_csv("prompts.csv")
        print(f"✅ Loaded CSV with {len(df)} rows.")
        print(f"Columns: {df.columns.tolist()}")
    except Exception as e:
        print(f"❌ Failed to load CSV: {e}")
        return

    print("\nTesting Logic Parsing (with Mock API)...")
    # Mock behavior
    mock_response = MagicMock()
    mock_response.text = """
    ```json
    {
        "original_prompt": "test prompt",
        "fan_out_queries": {
            "Search Intent": "Intent Query",
            "Contextual Layer": "Context Query",
            "Comparative Layer": "Compare Query",
            "Prerequisite": "Pre Query",
            "Next Step": "Next Query",
            "Entity Deep-Dive": "Deep Query"
        }
    }
    ```
    """
    fan_out_logic.genai.GenerativeModel.return_value.generate_content.return_value = mock_response
    
    # Run logic
    results_df = fan_out_logic.process_prompts(["test prompt"], api_key="dummy_key")
    
    if not results_df.empty and "Search Intent" in results_df.columns:
        print("✅ Logic processor worked correctly.")
        print(results_df.head())
    else:
        print("❌ Logic processor failed.")
        print(results_df)

if __name__ == "__main__":
    test_pipeline()
