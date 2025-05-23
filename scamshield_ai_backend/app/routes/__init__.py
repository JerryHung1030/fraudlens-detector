from .classification_router import router as classification_router
from .ingestion_router import router as ingestion_router # Add this line

__all__ = [
    "classification_router",
    "ingestion_router", # Add this line
]
