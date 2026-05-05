"""AWS Lambda handler for Orientation Mali.

Uses Mangum to adapt the FastAPI application for AWS Lambda + API Gateway.
"""

from mangum import Mangum

from src.orientation_mali.app import app

handler = Mangum(app, lifespan="off")
