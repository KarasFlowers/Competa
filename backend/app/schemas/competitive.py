from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class FeatureStatus(str, Enum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    MISSING = "missing"


class FeatureNode(BaseModel):
    name: str
    description: str = ""
    status: FeatureStatus = FeatureStatus.SUPPORTED
    children: list[FeatureNode] = Field(default_factory=list)


class FeatureTree(BaseModel):
    product_name: str
    root_nodes: list[FeatureNode] = Field(default_factory=list)


class PricingTier(BaseModel):
    name: str
    price: float
    currency: str = "USD"
    period: str = "monthly"
    features: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class PricingModelType(str, Enum):
    FREEMIUM = "freemium"
    SUBSCRIPTION = "subscription"
    ONE_TIME = "one_time"
    USAGE_BASED = "usage_based"


class PricingModel(BaseModel):
    product_name: str
    model_type: PricingModelType
    tiers: list[PricingTier] = Field(default_factory=list)


class Persona(BaseModel):
    segment_name: str
    demographics: str = ""
    pain_points: list[str] = Field(default_factory=list)
    needs: list[str] = Field(default_factory=list)
    product_usage_patterns: str = ""


class SWOTCategory(str, Enum):
    STRENGTH = "strength"
    WEAKNESS = "weakness"
    OPPORTUNITY = "opportunity"
    THREAT = "threat"


class SWOTItem(BaseModel):
    category: SWOTCategory
    content: str
    evidence_ids: list[str] = Field(default_factory=list)


class SWOT(BaseModel):
    product_name: str
    items: list[SWOTItem] = Field(default_factory=list)
