"""
CostEstimationEngine
Core algorithm for estimating government website development costs.

Methodology:
- Feature-based scoring: each detected feature adds a weighted cost
- Agency-type multiplier: ministry vs regency vs BUMN etc.
- Complexity classification: SIMPLE / MODERATE / COMPLEX / ENTERPRISE
- Indonesian market rates (2024): based on LKPP/SIRUP open data benchmarks
- Overhead model: PM 15%, Testing 10%, contingency buffer
"""

from backend.models.website_profile import (
    BudgetEstimate,
    ComplexityLevel,
    WebsiteMetrics,
    TechStack,
    WebsiteProfile,
)


class CostEstimationEngine:
    """
    Estimates Indonesian government website build cost in IDR.

    Rate basis (IDR, 2024 market rates):
    - Junior Dev: 6-8 juta/month
    - Mid Dev:   10-15 juta/month
    - Senior Dev: 20-30 juta/month
    - UX Designer: 8-15 juta/month
    - Project Manager: 10-20 juta/month
    - QA Engineer: 8-12 juta/month
    - Server/infra: varies by scale

    Reference: SIRUP LKPP procurement data, BPS salary survey,
    and ICT industry reports (APJII 2023, Gartner Southeast Asia benchmarks)
    """

    # Base rates per deliverable in IDR
    BASE_DESIGN_COST = 15_000_000       # Basic UI design 
    BASE_FRONTEND_COST = 20_000_000     # HTML/CSS/JS implementation
    BASE_BACKEND_COST = 25_000_000      # Basic dynamic pages, routing
    BASE_INFRA_COST = 12_000_000        # Shared hosting + domain setup
    BASE_CONTENT_COST = 5_000_000       # Initial content migration
    BASE_PM_RATE = 0.15                 # 15% of dev costs
    BASE_TESTING_RATE = 0.10            # 10% of dev costs
    BASE_ANNUAL_MAINTENANCE = 0.20      # 20% of build cost per year

    # Feature cost additions (IDR)
    FEATURE_COSTS = {
        "has_cms": 15_000_000,
        "has_database": 20_000_000,
        "has_api": 30_000_000,
        "has_search": 10_000_000,
        "has_map_integration": 8_000_000,
        "has_media_gallery": 7_000_000,
        "has_multilingual": 20_000_000,
        "has_login_system": 25_000_000,
        "has_mobile_responsive": 10_000_000,
        "has_custom_design": 15_000_000,
        "has_cdn": 5_000_000,
        "has_ssl": 2_000_000,
    }

    # Per subdomain cost (each subdomain = separate mini-site)
    SUBDOMAIN_COST = 30_000_000

    # Nav depth multiplier for frontend complexity
    NAV_DEPTH_MULTIPLIER = {1: 1.0, 2: 1.3, 3: 1.6, 4: 2.0}

    # Page count tiers: (max_pages, cost_per_page)
    PAGE_COST_TIERS = [
        (10, 1_500_000),
        (30, 1_200_000),
        (50, 900_000),
        (100, 700_000),
        (999, 500_000),
    ]

    # Agency type multiplier (risk, procurement overhead, specifications)
    AGENCY_MULTIPLIERS = {
        "kementerian": 2.5,       # Ministry-level: complex specs, high redundancy
        "badan": 2.0,             # National agency: moderate-high
        "lembaga": 1.8,           # Government body
        "provinsi": 1.6,          # Provincial government
        "kabupaten": 1.3,         # Regency/city government
        "kota": 1.3,
        "bumn": 1.5,              # State-owned enterprise
        "default": 1.5,
    }

    # Technology premium (if sophisticated stack detected)
    TECH_PREMIUM = {
        "next.js": 1.3,
        "react": 1.25,
        "vue": 1.2,
        "laravel": 1.15,
        "wordpress": 0.9,         # lower: template-based
        "drupal": 1.1,
        "joomla": 0.85,
        "unknown": 1.0,
    }

    def estimate(self, profile: WebsiteProfile) -> BudgetEstimate:
        """
        Main estimation method. Returns populated BudgetEstimate.
        """
        est = BudgetEstimate()
        notes = []
        metrics = profile.metrics
        tech = profile.tech_stack

        # --- 1. DESIGN COST ---
        design = self.BASE_DESIGN_COST
        if metrics.has_custom_design:
            design += 12_000_000
            notes.append("Custom design premium applied (+12jt)")
        if metrics.has_multilingual:
            design += 5_000_000
        est.design_cost = design

        # --- 2. FRONTEND DEVELOPMENT COST ---
        nav_mult = self.NAV_DEPTH_MULTIPLIER.get(metrics.nav_depth, 1.5)
        page_cost = self._calculate_page_cost(metrics.total_pages_estimated)
        frontend = self.BASE_FRONTEND_COST * nav_mult + page_cost
        if metrics.has_mobile_responsive:
            frontend += 10_000_000
        if metrics.has_media_gallery:
            frontend += 7_000_000
        if metrics.has_search:
            frontend += 5_000_000
        est.frontend_dev_cost = frontend
        notes.append(f"Pages estimated: {metrics.total_pages_estimated}, nav depth: {metrics.nav_depth}")

        # --- 3. BACKEND DEVELOPMENT COST ---
        backend = self.BASE_BACKEND_COST
        feature_map = {
            "has_cms": self.FEATURE_COSTS["has_cms"],
            "has_database": self.FEATURE_COSTS["has_database"],
            "has_api": self.FEATURE_COSTS["has_api"],
            "has_login_system": self.FEATURE_COSTS["has_login_system"],
            "has_map_integration": self.FEATURE_COSTS["has_map_integration"],
            "has_multilingual": self.FEATURE_COSTS["has_multilingual"],
        }
        for feature, cost in feature_map.items():
            if getattr(metrics, feature, False):
                backend += cost
                notes.append(f"Feature: {feature} (+{cost/1_000_000:.0f}jt)")
        est.backend_dev_cost = backend

        # --- 4. CMS INTEGRATION ---
        if metrics.has_cms and tech.cms:
            cms_cost = 20_000_000
            if tech.cms not in ("wordpress", "joomla"):
                cms_cost += 10_000_000  # custom CMS premium
            est.cms_integration_cost = cms_cost
            notes.append(f"CMS: {tech.cms} detected (+{cms_cost/1_000_000:.0f}jt)")
        else:
            est.cms_integration_cost = 0

        # --- 5. INFRASTRUCTURE ---
        infra = self.BASE_INFRA_COST
        if metrics.has_cdn:
            infra += 8_000_000
        if metrics.has_ssl:
            infra += 2_000_000
        # Subdomains add significant infra cost
        subdomain_count = len(metrics.subdomains)
        if subdomain_count > 0:
            infra += subdomain_count * self.SUBDOMAIN_COST
            notes.append(f"{subdomain_count} subdomains detected (+{subdomain_count * self.SUBDOMAIN_COST/1_000_000:.0f}jt)")
        est.infrastructure_cost = infra

        # --- 6. CONTENT COST ---
        content = self.BASE_CONTENT_COST + (metrics.total_pages_estimated * 300_000)
        est.content_cost = content

        # --- 7. SUBTOTAL BEFORE MULTIPLIERS ---
        raw_total = (
            est.design_cost
            + est.frontend_dev_cost
            + est.backend_dev_cost
            + est.cms_integration_cost
            + est.infrastructure_cost
            + est.content_cost
        )

        # --- 8. PM & TESTING ---
        est.project_management_cost = raw_total * self.BASE_PM_RATE
        est.testing_cost = raw_total * self.BASE_TESTING_RATE

        subtotal = raw_total + est.project_management_cost + est.testing_cost

        # --- 9. AGENCY TYPE MULTIPLIER ---
        agency_mult = self._get_agency_multiplier(profile.agency_type, profile.agency_name, profile.url)
        notes.append(f"Agency multiplier: {agency_mult}x ({profile.agency_type or 'default'})")

        # --- 10. TECH PREMIUM ---
        tech_name = (tech.cms or tech.framework or "unknown").lower()
        tech_mult = next(
            (v for k, v in self.TECH_PREMIUM.items() if k in tech_name),
            1.0
        )
        notes.append(f"Tech premium: {tech_mult}x ({tech_name})")

        # --- 11. GOVERNMENT PROCUREMENT OVERHEAD ---
        # Indonesian govt procurement adds 30-50% overhead:
        # KAK drafting, vendor selection, BAST, audit trail
        gov_overhead = 1.35
        notes.append(f"Govt procurement overhead: {gov_overhead}x")

        # --- 12. FINAL TOTAL ---
        final_total = subtotal * agency_mult * tech_mult * gov_overhead
        est.total_estimated = round(final_total, -6)  # Round to nearest million

        # --- 13. MAINTENANCE ---
        est.annual_maintenance_cost = round(est.total_estimated * self.BASE_ANNUAL_MAINTENANCE, -6)

        # --- 14. COMPLEXITY CLASSIFICATION ---
        profile.complexity = self._classify_complexity(metrics, est.total_estimated)
        notes.append(f"Complexity: {profile.complexity.value}")

        # --- 15. CONFIDENCE LEVEL ---
        est.confidence_level = self._assess_confidence(metrics)

        est.breakdown_notes = notes
        return est

    def _calculate_page_cost(self, page_count: int) -> float:
        total_cost = 0.0
        remaining = page_count
        prev_max = 0
        for max_pages, cost_per_page in self.PAGE_COST_TIERS:
            tier_pages = min(remaining, max_pages - prev_max)
            if tier_pages <= 0:
                break
            total_cost += tier_pages * cost_per_page
            remaining -= tier_pages
            prev_max = max_pages
            if remaining <= 0:
                break
        return total_cost

    def _get_agency_multiplier(self, agency_type: str, agency_name: str, url: str) -> float:
        combined = (agency_type + " " + agency_name + " " + url).lower()
        for key, mult in self.AGENCY_MULTIPLIERS.items():
            if key in combined:
                return mult
        return self.AGENCY_MULTIPLIERS["default"]

    def _classify_complexity(self, metrics: WebsiteMetrics, total: float) -> ComplexityLevel:
        score = 0
        score += metrics.has_cms * 1
        score += metrics.has_api * 2
        score += metrics.has_login_system * 2
        score += metrics.has_multilingual * 1
        score += metrics.has_map_integration * 1
        score += len(metrics.subdomains) * 1
        score += max(0, (metrics.nav_depth - 1))

        if score <= 2:
            return ComplexityLevel.SIMPLE
        elif score <= 5:
            return ComplexityLevel.MODERATE
        elif score <= 9:
            return ComplexityLevel.COMPLEX
        else:
            return ComplexityLevel.ENTERPRISE

    def _assess_confidence(self, metrics: WebsiteMetrics) -> str:
        signals = sum([
            metrics.has_ssl,
            metrics.has_cms,
            metrics.total_pages_estimated > 5,
            metrics.nav_depth > 1,
            metrics.total_nav_items > 10,
        ])
        if signals >= 4:
            return "High"
        elif signals >= 2:
            return "Medium"
        return "Low"
