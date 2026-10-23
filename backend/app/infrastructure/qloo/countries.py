"""ISO 3166-1 alpha-2 codes to the full English country names `filter.release_country` expects.

Qloo silently returns nothing for ISO codes ("US", "IN"), so the live adapter converts them.
Only "United States" and "India" have been checked live (docs/QLOO_NOTES.md, section 3).
"""

COUNTRY_NAMES: dict[str, str] = {
    "AR": "Argentina",
    "AU": "Australia",
    "AT": "Austria",
    "BD": "Bangladesh",
    "BE": "Belgium",
    "BR": "Brazil",
    "CA": "Canada",
    "CL": "Chile",
    "CN": "China",
    "CO": "Colombia",
    "CU": "Cuba",
    "DK": "Denmark",
    "EG": "Egypt",
    "FI": "Finland",
    "FR": "France",
    "DE": "Germany",
    "GR": "Greece",
    "HK": "Hong Kong",
    "HU": "Hungary",
    "IN": "India",
    "ID": "Indonesia",
    "IE": "Ireland",
    "IL": "Israel",
    "IT": "Italy",
    "JM": "Jamaica",
    "JP": "Japan",
    "KE": "Kenya",
    "KR": "South Korea",
    "LK": "Sri Lanka",
    "MY": "Malaysia",
    "MX": "Mexico",
    "NL": "Netherlands",
    "NZ": "New Zealand",
    "NG": "Nigeria",
    "NO": "Norway",
    "PK": "Pakistan",
    "PE": "Peru",
    "PH": "Philippines",
    "PL": "Poland",
    "PT": "Portugal",
    "PR": "Puerto Rico",
    "RU": "Russia",
    "SG": "Singapore",
    "ZA": "South Africa",
    "ES": "Spain",
    "SE": "Sweden",
    "CH": "Switzerland",
    "TW": "Taiwan",
    "TH": "Thailand",
    "TR": "Turkey",
    "AE": "United Arab Emirates",
    "GB": "United Kingdom",
    "US": "United States",
    "VN": "Vietnam",
}


def country_name(code: str) -> str | None:
    """The country's full English name, or None when we don't know the code."""
    return COUNTRY_NAMES.get(code.upper())
