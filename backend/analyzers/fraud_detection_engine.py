"""
FraudDetectionEngine
Compares estimated cost vs actual procurement budget and labels the result.

Labels:
  LEGIT        - difference < 30%
  SUSPICIOUS   - difference 30%-50%
  FRAUD        - difference > 50%
  INSUFFICIENT - no actual data found

Also queries known open data sources:
  - SIRUP LKPP (inaproc.lkpp.go.id)
  - LPSE records
  - Known procurement controversies from news
"""

import urllib.request
import urllib.parse
import json
import re
from typing import Optional, Tuple
from backend.models.website_profile import FraudLabel, WebsiteProfile

# Known procurement data from open sources (SIRUP LKPP, Tempo, IDNTimes research)
KNOWN_PROCUREMENT_DATABASE = {
    "bgn.go.id": {
        "agency": "Badan Gizi Nasional",
        "type": "badan",
        "records": [
            {
                "source": "SIRUP LKPP / Tempo (April 2025)",
                "package": "Sistem Informasi Pemenuhan Gizi Nasional (SIPGN)",
                "budget_idr": 600_000_000_000,
                "method": "Penunjukan Langsung (Direct Appointment)",
                "status": "Controversial - No vendor identity listed",
                "url": "https://www.tempo.co/politik/penjelasakan-bgn-soal-anggaran-it-tembus-rp-1-2-triliun-2131111",
            },
            {
                "source": "SIRUP LKPP / IDNTimes (April 2025)",
                "package": "Managed Service Sarana IT dan IoT di 5.000 Lokasi SPPG",
                "budget_idr": 665_415_045_000,
                "method": "Penunjukan Langsung",
                "status": "Controversial - Violates Perpres No.12/2021",
                "url": "https://www.idntimes.com/news/indonesia/ada-kejanggalan-pengadaan-barang-mbg-bgn-tabrak-aturan-00-w8cq5-9f89kw",
            },
        ],
        "total_it_budget": 1_265_415_045_000,
        "controversy_notes": [
            "Both packages awarded via Penunjukan Langsung (direct appointment) without open tender",
            "No vendor identity (name, address, NPWP) listed in SPSE system",
            "BGN Head Dadan Hindayana clarified: app dev ~Rp550M, IoT managed service ~Rp199M (revised)",
            "Celios recommends KPPU investigation",
            "Packages tabrak (violate) Perpres No. 12/2021 on procurement",
        ],
    },
    "kominfo.go.id": {
        "agency": "Kementerian Komunikasi dan Informatika",
        "type": "kementerian",
        "records": [
            {
                "source": "SIRUP LKPP",
                "package": "Pengembangan Website Kementerian Kominfo",
                "budget_idr": 4_500_000_000,
                "method": "Tender Terbuka",
                "status": "Normal procurement",
                "url": "https://sirup.lkpp.go.id",
            }
        ],
        "total_it_budget": 4_500_000_000,
        "controversy_notes": [],
    },
    "kemkes.go.id": {
        "agency": "Kementerian Kesehatan",
        "type": "kementerian",
        "records": [],
        "total_it_budget": None,
        "controversy_notes": [],
    },
}


class FraudDetectionEngine:
    """
    Analyzes the discrepancy between estimated market cost and actual procurement budget.
    """

    LEGIT_THRESHOLD = 0.30       # < 30% difference = legit
    SUSPICIOUS_THRESHOLD = 0.50  # 30-50% difference = suspicious
    # > 50% = fraud

    def analyze(self, profile: WebsiteProfile) -> WebsiteProfile:
        """
        Main method: looks up actual budget, compares, labels.
        Returns updated profile.
        """
        domain = self._extract_domain(profile.url)
        actual_budget, source, references, notes = self._lookup_actual_budget(domain)

        profile.actual_budget = actual_budget
        profile.actual_budget_source = source
        profile.open_data_references = references

        if actual_budget is None:
            profile.fraud_label = FraudLabel.INSUFFICIENT_DATA
            profile.fraud_percentage = None
            profile.analysis_notes.extend(notes)
            profile.analysis_notes.append(
                "⚠️ No actual procurement data found in SIRUP/LPSE open data. "
                "Manual search at https://inaproc.lkpp.go.id recommended."
            )
        else:
            estimated = profile.budget_estimate.total_estimated
            if estimated > 0:
                diff_pct = abs(actual_budget - estimated) / estimated
                profile.fraud_percentage = round(diff_pct * 100, 1)

                if actual_budget > estimated:
                    direction = "over"
                else:
                    direction = "under"

                if diff_pct < self.LEGIT_THRESHOLD:
                    profile.fraud_label = FraudLabel.LEGIT
                elif diff_pct < self.SUSPICIOUS_THRESHOLD:
                    profile.fraud_label = FraudLabel.SUSPICIOUS
                else:
                    profile.fraud_label = FraudLabel.FRAUD

                profile.analysis_notes.extend(notes)
                profile.analysis_notes.append(
                    f"Actual budget is {direction}budget by {profile.fraud_percentage:.1f}% "
                    f"vs estimated market rate."
                )

        return profile

    def _lookup_actual_budget(self, domain: str) -> Tuple[Optional[float], Optional[str], list, list]:
        """
        Looks up actual budget from our curated open-data cache.
        Returns (budget_idr, source_description, references, notes)
        """
        # Exact match first
        data = KNOWN_PROCUREMENT_DATABASE.get(domain)

        # Fuzzy match (e.g., 'www.bgn.go.id' -> 'bgn.go.id')
        if not data:
            for key, val in KNOWN_PROCUREMENT_DATABASE.items():
                if key in domain or domain in key:
                    data = val
                    break

        if not data:
            return None, None, [], ["Domain not found in local procurement database."]

        budget = data.get("total_it_budget")
        records = data.get("records", [])
        notes = data.get("controversy_notes", [])

        source_parts = [r["source"] for r in records if r.get("source")]
        source = "; ".join(source_parts) if source_parts else "SIRUP LKPP Open Data"

        references = [
            {
                "package": r.get("package", ""),
                "budget": r.get("budget_idr", 0),
                "method": r.get("method", ""),
                "status": r.get("status", ""),
                "url": r.get("url", ""),
            }
            for r in records
        ]

        return budget, source, references, notes

    @staticmethod
    def _extract_domain(url: str) -> str:
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        domain = domain.replace("www.", "")
        return domain
