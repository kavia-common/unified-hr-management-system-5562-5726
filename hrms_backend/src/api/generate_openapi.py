"""
Utility script to generate and write the OpenAPI schema to interfaces/openapi.json.

This script imports the FastAPI app to ensure routes and metadata are loaded,
then serializes the generated OpenAPI schema to disk.
"""

import json
import os

from src.api.main import app

# Get the OpenAPI schema
openapi_schema = app.openapi()

# Write to file
output_dir = "interfaces"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "openapi.json")

with open(output_path, "w") as f:
    json.dump(openapi_schema, f, indent=2)
