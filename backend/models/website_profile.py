"""
Website Profile Model
Stores all analyzed attributes of a government website for cost estimation.
"""
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class ComplexityLevel(Enum):
    SIMPLE = "Simple"
    MODERATE = "Moderate"
    COMPLEX = "Complex"
    ENTERPRISE = "Enterprise"


class FraudLabel(Enum):
    LEGIT = "LEGIT"
    SUSPICIOUS = "SUSPICIOUS"
    FRAUD = "FRAUD"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass
class TechStack:
    framework: str = "Unknown"
    cms: Optional[str] = None
    cdn: Optional[str] = None
    server: Optional[str] = None
    language: Optional[str] = None
    database: Optional[str] = None
    detected_libraries: list = field(default_factory=list)


@dataclass
class WebsiteMetrics:
    total_pages_estimated: int = 0
    has_cms: bool = False
    has_database: bool = False
    has_api: bool = False
    has_media_gallery: bool = False
    has_search: bool = False
    has_multilingual: bool = False
    has_map_integration: bool = False
    has_login_system: bool = False
    has_mobile_responsive: bool = False
    has_custom_design: bool = False
    nav_depth: int = 1
    total_nav_items: int = 0
    has_cdn: bool = False
    subdomains: list = field(default_factory=list)
    has_ssl: bool = False
    load_time_estimate: str = "Unknown"


@dataclass
class BudgetEstimate:
    design_cost: float = 0
    frontend_dev_cost: float = 0
    backend_dev_cost: float = 0
    cms_integration_cost: float = 0
    infrastructure_cost: float = 0
    content_cost: float = 0
    testing_cost: float = 0
    project_management_cost: float = 0
    annual_maintenance_cost: float = 0
    total_estimated: float = 0
    confidence_level: str = "Medium"
    breakdown_notes: list = field(default_factory=list)


@dataclass
class WebsiteProfile:
    url: str = ""
    agency_name: str = ""
    agency_type: str = ""
    complexity: ComplexityLevel = ComplexityLevel.SIMPLE
    tech_stack: TechStack = field(default_factory=TechStack)
    metrics: WebsiteMetrics = field(default_factory=WebsiteMetrics)
    budget_estimate: BudgetEstimate = field(default_factory=BudgetEstimate)
    actual_budget: Optional[float] = None
    actual_budget_source: Optional[str] = None
    fraud_label: FraudLabel = FraudLabel.INSUFFICIENT_DATA
    fraud_percentage: Optional[float] = None
    analysis_notes: list = field(default_factory=list)
    open_data_references: list = field(default_factory=list)
