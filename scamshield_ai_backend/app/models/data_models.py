from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

class PostMetadata(BaseModel):
    author: Optional[str] = None
    timestamp: Optional[str] = None # ISO datetime string
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    language: Optional[str] = None
    source: Optional[str] = None
    channel: Optional[str] = None # From updated example
    # Allow other arbitrary metadata fields
    class Config:
        extra = "allow"

class Post(BaseModel):
    sid: str
    text: str
    metadata: PostMetadata = Field(default_factory=PostMetadata)

class FraudScenarioMetadata(BaseModel):
    scenario: Optional[str] = None
    risk_level: Optional[str] = None
    language: Optional[str] = None
    # Allow other arbitrary metadata fields
    class Config:
        extra = "allow"

class FraudScenario(BaseModel):
    sid: str
    text: str
    metadata: FraudScenarioMetadata = Field(default_factory=FraudScenarioMetadata)
