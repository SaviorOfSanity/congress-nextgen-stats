"""
US Census Bureau and Congressional District Demographics Client
Provides demographic, economic, social safety net (SNAP/Medicaid), immigration, and partisan profiles for all 50 states and 435 US Congressional Districts.
"""
import json
import logging
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional
from backend.config import CACHE_DIR, CENSUS_API_KEY
from backend.models import ConstituentDemographics

logger = logging.getLogger(__name__)

STATE_FIPS_TO_ABBR: Dict[str, str] = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT",
    "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL",
    "18": "IN", "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD",
    "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT", "31": "NE",
    "32": "NV", "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA", "54": "WV",
    "55": "WI", "56": "WY", "60": "AS", "66": "GU", "69": "MP", "72": "PR", "78": "VI",
}
STATE_ABBR_TO_FIPS: Dict[str, str] = {v: k for k, v in STATE_FIPS_TO_ABBR.items()}
_CENSUS_ACS_CACHE_PATH = CACHE_DIR / "census_acs_cache.json"
_CENSUS_ACS_CACHE: Optional[Dict[str, Any]] = None

# State-level baseline profiles across all 50 states + territories
STATE_BASELINES: Dict[str, Dict] = {
    "AL": {"income": 59609, "poverty": 15.6, "snap": 14.2, "medicaid": 23.5, "foreign_born": 3.7, "uninsured": 9.7, "urban": 59.0, "college": 27.4, "veteran": 8.6, "pvi": "R+15", "top_sectors": {"Manufacturing": 14.8, "Healthcare": 13.5, "Defense/Aerospace": 7.2, "Agriculture": 4.1}},
    "AK": {"income": 86370, "poverty": 10.7, "snap": 10.1, "medicaid": 26.2, "foreign_born": 8.2, "uninsured": 11.2, "urban": 66.0, "college": 31.0, "veteran": 11.5, "pvi": "R+8", "top_sectors": {"Oil & Gas": 16.2, "Maritime/Fishing": 12.1, "Defense": 9.5, "Tourism": 8.2}},
    "AZ": {"income": 72581, "poverty": 12.5, "snap": 11.8, "medicaid": 25.1, "foreign_born": 13.1, "uninsured": 10.2, "urban": 89.3, "college": 31.2, "veteran": 8.7, "pvi": "R+2", "top_sectors": {"Semiconductors/Tech": 11.5, "Healthcare": 13.4, "Tourism": 11.2, "Defense": 6.8}},
    "AR": {"income": 56335, "poverty": 16.0, "snap": 13.5, "medicaid": 28.4, "foreign_born": 5.1, "uninsured": 8.9, "urban": 56.2, "college": 24.3, "veteran": 8.1, "pvi": "R+16", "top_sectors": {"Agribusiness/Poultry": 16.2, "Retail/Logistics": 14.5, "Healthcare": 13.1, "Manufacturing": 11.0}},
    "CA": {"income": 91905, "poverty": 12.0, "snap": 10.5, "medicaid": 34.2, "foreign_born": 26.8, "uninsured": 6.5, "urban": 94.2, "college": 35.3, "veteran": 4.8, "pvi": "D+14", "top_sectors": {"Tech": 15.5, "Healthcare": 13.8, "Agriculture": 5.2, "Entertainment": 6.5}},
    "CO": {"income": 87598, "poverty": 9.4, "snap": 7.9, "medicaid": 22.1, "foreign_born": 9.8, "uninsured": 7.4, "urban": 86.2, "college": 42.8, "veteran": 8.3, "pvi": "D+4", "top_sectors": {"Aerospace/Defense": 11.8, "Tech": 14.2, "Tourism/Outdoor": 9.5, "Energy": 6.4}},
    "CT": {"income": 90215, "poverty": 10.1, "snap": 12.1, "medicaid": 24.8, "foreign_born": 15.2, "uninsured": 5.1, "urban": 88.0, "college": 40.6, "veteran": 5.1, "pvi": "D+11", "top_sectors": {"Insurance/Finance": 17.5, "Defense/Submarines": 12.4, "Healthcare": 14.5, "Biotech": 7.8}},
    "DE": {"income": 79325, "poverty": 11.6, "snap": 12.4, "medicaid": 25.4, "foreign_born": 10.1, "uninsured": 5.7, "urban": 83.3, "college": 34.5, "veteran": 7.5, "pvi": "D+7", "top_sectors": {"Banking/Credit": 18.2, "Chemicals/Pharma": 11.5, "Healthcare": 13.8, "Poultry": 5.2}},
    "FL": {"income": 67917, "poverty": 13.1, "snap": 14.8, "medicaid": 23.2, "foreign_born": 21.6, "uninsured": 11.8, "urban": 91.2, "college": 31.5, "veteran": 8.9, "pvi": "R+6", "top_sectors": {"Tourism/Hospitality": 15.4, "Healthcare": 14.2, "Real Estate": 9.8, "Defense": 6.2}},
    "GA": {"income": 71355, "poverty": 13.5, "snap": 13.1, "medicaid": 21.8, "foreign_born": 10.4, "uninsured": 11.7, "urban": 75.1, "college": 33.0, "veteran": 8.0, "pvi": "R+3", "top_sectors": {"Logistics/Transport": 12.4, "Healthcare": 12.0, "Tech": 8.8, "Agriculture": 5.9}},
    "HI": {"income": 94814, "poverty": 10.2, "snap": 11.5, "medicaid": 26.5, "foreign_born": 18.5, "uninsured": 3.8, "urban": 92.0, "college": 34.8, "veteran": 9.1, "pvi": "D+15", "top_sectors": {"Tourism/Hospitality": 22.5, "Defense/Military": 14.2, "Healthcare": 12.1, "Maritime": 5.8}},
    "ID": {"income": 70331, "poverty": 11.0, "snap": 8.2, "medicaid": 22.8, "foreign_born": 6.1, "uninsured": 8.8, "urban": 70.6, "college": 29.5, "veteran": 8.9, "pvi": "R+19", "top_sectors": {"Agriculture/Food": 15.4, "Semiconductors/Tech": 12.1, "Construction": 10.2, "Healthcare": 11.8}},
    "IL": {"income": 78433, "poverty": 11.9, "snap": 13.2, "medicaid": 26.5, "foreign_born": 14.2, "uninsured": 6.5, "urban": 87.5, "college": 35.8, "veteran": 5.3, "pvi": "D+7", "top_sectors": {"Finance": 13.5, "Manufacturing": 11.8, "Agriculture": 6.1, "Healthcare": 13.5}},
    "IN": {"income": 67173, "poverty": 12.6, "snap": 9.8, "medicaid": 27.5, "foreign_born": 5.5, "uninsured": 7.5, "urban": 72.4, "college": 28.5, "veteran": 6.8, "pvi": "R+11", "top_sectors": {"Manufacturing/Auto": 19.8, "Healthcare": 13.2, "Agriculture": 5.8, "Logistics": 9.5}},
    "IA": {"income": 70571, "poverty": 11.1, "snap": 9.2, "medicaid": 22.4, "foreign_born": 5.8, "uninsured": 4.8, "urban": 64.0, "college": 30.2, "veteran": 6.5, "pvi": "R+6", "top_sectors": {"Agribusiness/Corn": 18.5, "Insurance/Fintech": 12.2, "Manufacturing": 13.1, "Healthcare": 12.5}},
    "KS": {"income": 71967, "poverty": 11.5, "snap": 7.8, "medicaid": 16.5, "foreign_born": 7.4, "uninsured": 8.6, "urban": 74.2, "college": 34.1, "veteran": 7.8, "pvi": "R+11", "top_sectors": {"Aviation/Aerospace": 14.2, "Agriculture/Cattle": 15.8, "Healthcare": 12.4, "Energy": 6.2}},
    "KY": {"income": 60183, "poverty": 16.5, "snap": 15.8, "medicaid": 33.2, "foreign_born": 4.1, "uninsured": 5.6, "urban": 58.4, "college": 25.0, "veteran": 8.1, "pvi": "R+16", "top_sectors": {"Manufacturing/Auto": 15.8, "Logistics/UPS": 11.5, "Healthcare": 14.0, "Energy/Coal": 6.8}},
    "LA": {"income": 57945, "poverty": 18.6, "snap": 18.2, "medicaid": 38.5, "foreign_born": 4.5, "uninsured": 8.1, "urban": 73.2, "college": 25.5, "veteran": 7.2, "pvi": "R+12", "top_sectors": {"Petrochemicals/Energy": 17.5, "Maritime/Ports": 13.2, "Healthcare": 13.8, "Tourism": 8.5}},
    "ME": {"income": 68251, "poverty": 10.8, "snap": 13.5, "medicaid": 26.8, "foreign_born": 3.9, "uninsured": 6.5, "urban": 38.7, "college": 34.0, "veteran": 9.5, "pvi": "D+2", "top_sectors": {"Shipbuilding/Defense": 14.2, "Forestry/Paper": 10.5, "Healthcare": 16.8, "Tourism": 11.2}},
    "MD": {"income": 98461, "poverty": 9.6, "snap": 11.2, "medicaid": 24.2, "foreign_born": 15.8, "uninsured": 5.8, "urban": 87.2, "college": 41.5, "veteran": 6.8, "pvi": "D+14", "top_sectors": {"Federal Govt/Defense": 22.4, "Biotech/Pharma": 14.2, "Healthcare": 13.5, "Cybersecurity": 11.8}},
    "MA": {"income": 96505, "poverty": 10.4, "snap": 12.8, "medicaid": 27.5, "foreign_born": 17.4, "uninsured": 2.5, "urban": 92.0, "college": 45.2, "veteran": 4.2, "pvi": "D+15", "top_sectors": {"Biotech/Life Sciences": 18.5, "Higher Education": 14.2, "Finance": 13.1, "Healthcare": 16.2}},
    "MI": {"income": 68505, "poverty": 13.1, "snap": 13.8, "medicaid": 28.5, "foreign_born": 6.9, "uninsured": 5.2, "urban": 73.8, "college": 30.6, "veteran": 6.2, "pvi": "R+1", "top_sectors": {"Automotive/Manufacturing": 18.2, "Healthcare": 13.9, "Tech": 7.4, "Agriculture": 4.8}},
    "MN": {"income": 84313, "poverty": 9.6, "snap": 8.4, "medicaid": 21.2, "foreign_born": 8.7, "uninsured": 4.1, "urban": 73.3, "college": 37.0, "veteran": 6.4, "pvi": "D+1", "top_sectors": {"Medical Devices/Health": 17.2, "Agribusiness/Target": 14.5, "Manufacturing": 12.4, "Fintech": 8.5}},
    "MS": {"income": 52985, "poverty": 19.1, "snap": 16.5, "medicaid": 29.5, "foreign_born": 2.6, "uninsured": 11.9, "urban": 46.4, "college": 23.2, "veteran": 6.8, "pvi": "R+11", "top_sectors": {"Shipbuilding/Defense": 12.5, "Agriculture/Timber": 16.4, "Healthcare": 14.2, "Manufacturing": 12.0}},
    "MO": {"income": 67111, "poverty": 12.7, "snap": 10.8, "medicaid": 24.5, "foreign_born": 4.4, "uninsured": 8.6, "urban": 70.4, "college": 30.5, "veteran": 7.9, "pvi": "R+10", "top_sectors": {"Aerospace/Defense": 12.8, "Agribusiness": 13.5, "Healthcare": 14.5, "Manufacturing": 11.2}},
    "MT": {"income": 69820, "poverty": 12.2, "snap": 8.9, "medicaid": 23.5, "foreign_born": 2.5, "uninsured": 8.2, "urban": 55.9, "college": 33.5, "veteran": 9.8, "pvi": "R+11", "top_sectors": {"Agriculture/Cattle": 16.5, "Mining/Energy": 11.2, "Tourism": 12.4, "Healthcare": 13.0}},
    "NE": {"income": 73070, "poverty": 10.5, "snap": 8.5, "medicaid": 19.2, "foreign_born": 7.2, "uninsured": 7.1, "urban": 73.1, "college": 33.2, "veteran": 6.7, "pvi": "R+13", "top_sectors": {"Agribusiness/Meatpacking": 19.2, "Rail/Logistics": 12.5, "Insurance": 11.0, "Healthcare": 12.4}},
    "NV": {"income": 71646, "poverty": 13.0, "snap": 14.1, "medicaid": 28.5, "foreign_born": 19.2, "uninsured": 11.4, "urban": 94.2, "college": 26.2, "veteran": 8.4, "pvi": "EVEN", "top_sectors": {"Gaming/Hospitality": 24.5, "Mining/Lithium": 8.5, "Construction": 10.2, "Healthcare": 11.2}},
    "NH": {"income": 90845, "poverty": 7.2, "snap": 6.8, "medicaid": 17.5, "foreign_born": 6.4, "uninsured": 5.4, "urban": 60.3, "college": 38.5, "veteran": 8.5, "pvi": "D+1", "top_sectors": {"High Tech/Defense": 15.8, "Healthcare": 14.5, "Tourism": 10.2, "Manufacturing": 11.5}},
    "NJ": {"income": 97126, "poverty": 9.7, "snap": 10.5, "medicaid": 23.8, "foreign_born": 23.2, "uninsured": 6.8, "urban": 94.7, "college": 41.5, "veteran": 4.1, "pvi": "D+6", "top_sectors": {"Pharma/Biotech": 18.2, "Finance/Wall St": 16.5, "Logistics/Ports": 12.4, "Healthcare": 14.0}},
    "NM": {"income": 58722, "poverty": 18.2, "snap": 21.5, "medicaid": 42.5, "foreign_born": 9.5, "uninsured": 8.2, "urban": 77.4, "college": 28.5, "veteran": 8.2, "pvi": "D+3", "top_sectors": {"National Labs/Defense": 16.5, "Oil & Gas": 14.2, "Healthcare": 15.0, "Tourism": 8.2}},
    "NY": {"income": 81386, "poverty": 13.9, "snap": 15.8, "medicaid": 36.8, "foreign_born": 22.8, "uninsured": 4.9, "urban": 87.4, "college": 37.8, "veteran": 4.5, "pvi": "D+10", "top_sectors": {"Finance": 16.8, "Healthcare": 16.2, "Tech": 9.5, "Education": 10.4}},
    "NC": {"income": 66186, "poverty": 13.4, "snap": 13.2, "medicaid": 24.5, "foreign_born": 8.5, "uninsured": 9.8, "urban": 66.1, "college": 32.7, "veteran": 8.6, "pvi": "R+3", "top_sectors": {"Banking": 11.5, "Biotech/Pharma": 9.5, "Manufacturing": 10.8, "Defense": 7.5}},
    "ND": {"income": 73650, "poverty": 10.8, "snap": 6.8, "medicaid": 16.8, "foreign_born": 4.8, "uninsured": 6.8, "urban": 59.9, "college": 31.5, "veteran": 7.2, "pvi": "R+20", "top_sectors": {"Oil/Bakken": 18.5, "Agriculture/Wheat": 16.2, "Healthcare": 12.5, "Manufacturing": 8.5}},
    "OH": {"income": 65720, "poverty": 13.4, "snap": 13.5, "medicaid": 27.5, "foreign_born": 4.8, "uninsured": 6.5, "urban": 77.9, "college": 29.3, "veteran": 7.2, "pvi": "R+6", "top_sectors": {"Manufacturing": 16.5, "Healthcare": 14.1, "Agriculture": 5.1, "Logistics": 8.3}},
    "OK": {"income": 61364, "poverty": 15.2, "snap": 14.5, "medicaid": 31.2, "foreign_born": 6.2, "uninsured": 13.8, "urban": 66.2, "college": 26.5, "veteran": 8.8, "pvi": "R+20", "top_sectors": {"Oil & Gas": 16.8, "Aerospace/Defense": 11.5, "Agriculture": 10.2, "Healthcare": 12.5}},
    "OR": {"income": 76632, "poverty": 11.9, "snap": 16.2, "medicaid": 30.5, "foreign_born": 9.8, "uninsured": 5.2, "urban": 81.0, "college": 35.5, "veteran": 7.8, "pvi": "D+6", "top_sectors": {"Silicon Forest/Tech": 14.5, "Forestry/Timber": 9.8, "Healthcare": 13.5, "Agriculture": 6.2}},
    "PA": {"income": 73170, "poverty": 11.8, "snap": 13.2, "medicaid": 26.8, "foreign_born": 7.2, "uninsured": 5.5, "urban": 76.5, "college": 32.3, "veteran": 6.8, "pvi": "R+1", "top_sectors": {"Healthcare": 16.2, "Manufacturing": 11.5, "Energy": 7.2, "Education": 9.5}},
    "RI": {"income": 81370, "poverty": 11.4, "snap": 15.5, "medicaid": 31.2, "foreign_born": 14.1, "uninsured": 4.2, "urban": 90.7, "college": 34.5, "veteran": 5.8, "pvi": "D+8", "top_sectors": {"Defense/Submarines": 15.2, "Healthcare": 16.0, "Higher Education": 11.2, "Tourism": 7.8}},
    "SC": {"income": 63623, "poverty": 14.5, "snap": 13.8, "medicaid": 23.5, "foreign_born": 5.5, "uninsured": 10.4, "urban": 66.3, "college": 29.8, "veteran": 9.2, "pvi": "R+8", "top_sectors": {"Automotive/Aerospace": 16.5, "Tourism/Charleston": 12.5, "Healthcare": 12.8, "Ports": 7.2}},
    "SD": {"income": 69457, "poverty": 11.8, "snap": 8.5, "medicaid": 18.5, "foreign_born": 4.1, "uninsured": 8.4, "urban": 56.7, "college": 30.5, "veteran": 8.1, "pvi": "R+16", "top_sectors": {"Banking/Credit": 14.5, "Agriculture/Soy": 17.2, "Healthcare": 13.5, "Tourism": 7.8}},
    "TN": {"income": 64035, "poverty": 13.6, "snap": 13.5, "medicaid": 23.8, "foreign_born": 5.8, "uninsured": 9.8, "urban": 66.4, "college": 29.2, "veteran": 7.8, "pvi": "R+14", "top_sectors": {"Healthcare HQ": 15.2, "Auto Manufacturing": 14.5, "Music/Hospitality": 10.5, "Logistics": 8.9}},
    "TX": {"income": 73035, "poverty": 13.9, "snap": 13.2, "medicaid": 20.8, "foreign_born": 17.5, "uninsured": 16.6, "urban": 83.7, "college": 31.5, "veteran": 7.1, "pvi": "R+8", "top_sectors": {"Energy/Oil": 12.5, "Healthcare": 12.5, "Defense/Aerospace": 8.2, "Tech": 9.5}},
    "UT": {"income": 87649, "poverty": 8.6, "snap": 5.8, "medicaid": 14.8, "foreign_born": 8.8, "uninsured": 9.2, "urban": 90.6, "college": 35.8, "veteran": 5.2, "pvi": "R+13", "top_sectors": {"Silicon Slopes/Tech": 16.2, "Defense/Aerospace": 11.5, "Tourism/Ski": 9.8, "Healthcare": 11.5}},
    "VT": {"income": 74070, "poverty": 10.5, "snap": 11.2, "medicaid": 27.5, "foreign_born": 4.8, "uninsured": 4.1, "urban": 35.1, "college": 40.5, "veteran": 6.8, "pvi": "D+16", "top_sectors": {"Healthcare": 16.5, "Higher Education": 12.8, "Tourism": 11.5, "Specialty Ag": 8.2}},
    "VA": {"income": 89963, "poverty": 9.9, "snap": 9.5, "medicaid": 21.5, "foreign_born": 12.8, "uninsured": 7.2, "urban": 75.5, "college": 40.2, "veteran": 9.8, "pvi": "D+3", "top_sectors": {"Defense/Pentagon/Navy": 21.5, "Tech/Data Centers": 15.2, "Healthcare": 12.5, "Ag": 5.1}},
    "WA": {"income": 90325, "poverty": 9.9, "snap": 11.5, "medicaid": 27.5, "foreign_born": 15.2, "uninsured": 5.8, "urban": 83.4, "college": 37.3, "veteran": 7.9, "pvi": "D+8", "top_sectors": {"Cloud/Tech": 18.5, "Aerospace/Boeing": 12.8, "Maritime": 6.5, "Ag": 6.2}},
    "WV": {"income": 55216, "poverty": 16.8, "snap": 16.8, "medicaid": 34.5, "foreign_born": 1.8, "uninsured": 5.8, "urban": 48.7, "college": 21.5, "veteran": 8.8, "pvi": "R+22", "top_sectors": {"Energy/Coal/Gas": 15.2, "Healthcare": 16.8, "Manufacturing": 9.5, "Tourism": 7.2}},
    "WI": {"income": 72458, "poverty": 10.8, "snap": 10.5, "medicaid": 22.5, "foreign_born": 5.1, "uninsured": 5.2, "urban": 70.2, "college": 31.8, "veteran": 6.5, "pvi": "R+2", "top_sectors": {"Manufacturing": 17.5, "Dairy/Ag": 12.8, "Healthcare": 13.8, "Paper/Forestry": 6.8}},
    "WY": {"income": 71052, "poverty": 10.9, "snap": 5.9, "medicaid": 14.5, "foreign_born": 3.5, "uninsured": 11.5, "urban": 64.8, "college": 29.5, "veteran": 9.5, "pvi": "R+25", "top_sectors": {"Mining/Oil/Coal": 21.5, "Tourism/Parks": 13.2, "Agriculture": 10.5, "Healthcare": 10.2}},
    # Federal District & U.S. Territories
    "DC": {"income": 101722, "poverty": 14.2, "snap": 18.5, "medicaid": 31.0, "foreign_born": 13.8, "uninsured": 3.4, "urban": 100.0, "college": 63.0, "veteran": 4.2, "pvi": "D+43", "top_sectors": {"Federal Government": 26.5, "Professional Services": 18.2, "Healthcare": 12.5, "Higher Education": 10.4}},
    "PR": {"income": 25621, "poverty": 40.5, "snap": 42.0, "medicaid": 46.5, "foreign_born": 2.9, "uninsured": 6.2, "urban": 92.0, "college": 28.5, "veteran": 3.1, "pvi": "EVEN", "top_sectors": {"Pharma/Medical Mfg": 14.8, "Tourism/Hospitality": 12.2, "Healthcare": 13.5, "Public Admin": 15.0}},
    "VI": {"income": 40408, "poverty": 22.8, "snap": 24.0, "medicaid": 28.0, "foreign_born": 35.0, "uninsured": 22.0, "urban": 94.0, "college": 21.0, "veteran": 4.5, "pvi": "D+15", "top_sectors": {"Tourism/Hospitality": 28.0, "Public Admin": 20.0, "Maritime/Refining": 10.5, "Retail": 14.0}},
    "GU": {"income": 58289, "poverty": 20.2, "snap": 26.0, "medicaid": 25.0, "foreign_born": 32.0, "uninsured": 18.0, "urban": 93.0, "college": 22.5, "veteran": 8.9, "pvi": "EVEN", "top_sectors": {"Defense/Military Base": 24.0, "Tourism": 22.0, "Construction": 11.5, "Public Admin": 16.5}},
    "AS": {"income": 28352, "poverty": 54.0, "snap": 38.0, "medicaid": 45.0, "foreign_born": 34.0, "uninsured": 19.0, "urban": 87.0, "college": 14.0, "veteran": 6.2, "pvi": "EVEN", "top_sectors": {"Tuna/Fisheries Mfg": 31.0, "Public Admin": 28.0, "Healthcare": 10.0, "Retail": 11.0}},
    "MP": {"income": 31362, "poverty": 38.0, "snap": 35.0, "medicaid": 42.0, "foreign_born": 39.0, "uninsured": 20.0, "urban": 89.0, "college": 19.5, "veteran": 4.8, "pvi": "EVEN", "top_sectors": {"Tourism/Hospitality": 32.0, "Public Admin": 24.0, "Construction": 12.0, "Retail": 13.0}}
}

# Representative 5-digit ZIP -> Congressional District mappings
ZIP_TO_DISTRICT_MAP: Dict[str, Dict] = {
    "10457": {"state": "NY", "district": 14},  # Bronx/Queens NY-14
    "11372": {"state": "NY", "district": 14},
    "10001": {"state": "NY", "district": 12},
    "11201": {"state": "NY", "district": 7},
    "11216": {"state": "NY", "district": 8},   # Brooklyn NY-08
    "94102": {"state": "CA", "district": 11},  # San Francisco CA-11
    "95014": {"state": "CA", "district": 17},  # Silicon Valley CA-17
    "90001": {"state": "CA", "district": 43},
    "04401": {"state": "ME", "district": 2},   # Bangor ME-02
    "45801": {"state": "OH", "district": 4},   # Lima OH-04
    "70001": {"state": "LA", "district": 1},   # Metairie LA-01
    "41011": {"state": "KY", "district": 4},   # Northern KY-04
    "30720": {"state": "GA", "district": 14},  # Dalton GA-14
    "20001": {"state": "DC", "district": 0},   # Washington DC
    "00901": {"state": "PR", "district": 0},   # San Juan PR
    "96950": {"state": "MP", "district": 0},   # Saipan MP
    "05401": {"state": "VT", "district": 0},   # Burlington VT At-Large
    "78701": {"state": "TX", "district": 37},
    "60601": {"state": "IL", "district": 7},
    "33101": {"state": "FL", "district": 24},
    "02108": {"state": "MA", "district": 8},
    "98101": {"state": "WA", "district": 7},
    "80202": {"state": "CO", "district": 1},
    "85004": {"state": "AZ", "district": 3},
}


def resolve_zip_to_state_district(zip_code: str) -> Dict[str, Optional[int]]:
    """Resolve a 5-digit ZIP code to (state, exact_or_estimated_district)."""
    z = (zip_code or "").strip()
    if z in ZIP_TO_DISTRICT_MAP:
        entry = ZIP_TO_DISTRICT_MAP[z]
        return {"state": entry["state"], "district": entry.get("district"), "exact_district_match": True}

    if not z.isdigit() or len(z) < 3:
        return {"state": "NY", "district": 14, "exact_district_match": False}

    prefix = int(z[:3])
    zip_num = int(z) if len(z) == 5 else prefix * 100

    # Specific territory / DC prefixes
    if zip_num == 96799:
        st = "AS"
    elif 96910 <= zip_num <= 96932:
        st = "GU"
    elif 96950 <= zip_num <= 96952:
        st = "MP"
    elif prefix == 5:
        st = "NY"
    elif 6 <= prefix <= 7 or prefix == 9:
        st = "PR"
    elif prefix == 8:
        st = "VI"
    elif 10 <= prefix <= 27:
        st = "MA"
    elif 28 <= prefix <= 29:
        st = "RI"
    elif 30 <= prefix <= 38:
        st = "NH"
    elif 39 <= prefix <= 49:
        st = "ME"
    elif 50 <= prefix <= 59:
        st = "VT"
    elif 60 <= prefix <= 69:
        st = "CT"
    elif 70 <= prefix <= 89:
        st = "NJ"
    elif 100 <= prefix <= 149:
        st = "NY"
    elif 150 <= prefix <= 196:
        st = "PA"
    elif 197 <= prefix <= 199:
        st = "DE"
    elif prefix in (200, 202, 203, 204, 205):
        st = "DC"
    elif prefix == 201 or (220 <= prefix <= 246):
        st = "VA"
    elif 206 <= prefix <= 219:
        st = "MD"
    elif 247 <= prefix <= 268:
        st = "WV"
    elif 270 <= prefix <= 289:
        st = "NC"
    elif 290 <= prefix <= 299:
        st = "SC"
    elif (300 <= prefix <= 319) or prefix in (398, 399):
        st = "GA"
    elif 320 <= prefix <= 349:
        st = "FL"
    elif 350 <= prefix <= 369:
        st = "AL"
    elif 370 <= prefix <= 385:
        st = "TN"
    elif 386 <= prefix <= 397:
        st = "MS"
    elif 400 <= prefix <= 427:
        st = "KY"
    elif 430 <= prefix <= 459:
        st = "OH"
    elif 460 <= prefix <= 479:
        st = "IN"
    elif 480 <= prefix <= 499:
        st = "MI"
    elif 500 <= prefix <= 528:
        st = "IA"
    elif 530 <= prefix <= 549:
        st = "WI"
    elif 550 <= prefix <= 567:
        st = "MN"
    elif 570 <= prefix <= 577:
        st = "SD"
    elif 580 <= prefix <= 588:
        st = "ND"
    elif 590 <= prefix <= 599:
        st = "MT"
    elif 600 <= prefix <= 629:
        st = "IL"
    elif 630 <= prefix <= 658:
        st = "MO"
    elif 660 <= prefix <= 679:
        st = "KS"
    elif 680 <= prefix <= 693:
        st = "NE"
    elif 700 <= prefix <= 714:
        st = "LA"
    elif 716 <= prefix <= 729:
        st = "AR"
    elif 730 <= prefix <= 749:
        st = "OK"
    elif (750 <= prefix <= 799) or prefix == 885:
        st = "TX"
    elif 800 <= prefix <= 816:
        st = "CO"
    elif 820 <= prefix <= 831:
        st = "WY"
    elif 832 <= prefix <= 838:
        st = "ID"
    elif 840 <= prefix <= 847:
        st = "UT"
    elif 850 <= prefix <= 865:
        st = "AZ"
    elif 870 <= prefix <= 884:
        st = "NM"
    elif 889 <= prefix <= 898:
        st = "NV"
    elif 900 <= prefix <= 961:
        st = "CA"
    elif 967 <= prefix <= 968:
        st = "HI"
    elif 970 <= prefix <= 979:
        st = "OR"
    elif 980 <= prefix <= 994:
        st = "WA"
    elif 995 <= prefix <= 999:
        st = "AK"
    else:
        st = "NY"

    return {"state": st, "district": None, "exact_district_match": False}

# Granular Representative District Overrides for Notable Districts
DISTRICT_PROFILES: Dict[str, Dict] = {
    "NY-14": {"income": 68400, "poverty": 16.2, "snap": 22.4, "medicaid": 34.5, "foreign_born": 46.2, "uninsured": 12.8, "disability": 9.8, "urban": 100.0, "college": 31.8, "veteran": 1.9, "pvi": "D+28", "top_sectors": {"Healthcare & Social": 22.4, "Service & Retail": 19.8, "Transportation": 11.5, "Hospitality": 10.2}},
    "CA-11": {"income": 138500, "poverty": 8.5, "snap": 8.2, "medicaid": 18.2, "foreign_born": 34.8, "uninsured": 4.5, "disability": 9.2, "urban": 99.1, "college": 61.2, "veteran": 3.1, "pvi": "D+34", "top_sectors": {"Tech & AI": 29.5, "Biotech/Health": 16.2, "Finance": 14.1, "Education": 12.0}},
    "NY-08": {"income": 74500, "poverty": 17.5, "snap": 24.8, "medicaid": 36.2, "foreign_born": 35.4, "uninsured": 7.2, "disability": 11.5, "urban": 100.0, "college": 36.5, "veteran": 2.5, "pvi": "D+26", "top_sectors": {"Healthcare": 24.2, "Education": 14.5, "Finance": 12.8, "Public Admin": 11.2}},
    "CA-17": {"income": 162000, "poverty": 6.2, "snap": 4.5, "medicaid": 11.5, "foreign_born": 52.8, "uninsured": 3.8, "disability": 6.5, "urban": 98.5, "college": 66.8, "veteran": 2.2, "pvi": "D+23", "top_sectors": {"Semiconductors & Tech": 38.5, "Software": 21.2, "Biotech": 12.0, "Finance": 9.5}},
    "ME-02": {"income": 58200, "poverty": 13.8, "snap": 15.2, "medicaid": 28.5, "foreign_born": 2.4, "uninsured": 7.9, "disability": 18.4, "urban": 32.5, "college": 24.5, "veteran": 10.8, "pvi": "R+6", "top_sectors": {"Paper & Timber": 15.2, "Defense (BIW Shipyard)": 14.5, "Healthcare": 16.8, "Lobster/Fishing": 9.2}},
    "OH-04": {"income": 61200, "poverty": 12.8, "snap": 11.8, "medicaid": 19.4, "foreign_born": 2.1, "uninsured": 7.2, "disability": 14.5, "urban": 48.2, "college": 21.5, "veteran": 7.8, "pvi": "R+20", "top_sectors": {"Manufacturing": 24.8, "Agriculture": 14.2, "Healthcare": 11.5, "Logistics": 9.8}},
    "LA-01": {"income": 69800, "poverty": 13.5, "snap": 12.5, "medicaid": 22.1, "foreign_born": 6.8, "uninsured": 9.8, "disability": 15.2, "urban": 78.4, "college": 33.1, "veteran": 8.2, "pvi": "R+23", "top_sectors": {"Oil & Gas Energy": 18.5, "Maritime & Ports": 14.2, "Defense": 9.1, "Healthcare": 12.0}},
    "KY-04": {"income": 68500, "poverty": 11.2, "snap": 10.4, "medicaid": 18.9, "foreign_born": 3.5, "uninsured": 6.8, "disability": 13.8, "urban": 68.2, "college": 29.5, "veteran": 7.9, "pvi": "R+19", "top_sectors": {"Manufacturing & Auto": 19.2, "Logistics (Amazon Hub)": 16.5, "Healthcare": 12.8, "Agriculture": 6.5}},
    "GA-14": {"income": 58900, "poverty": 15.1, "snap": 15.8, "medicaid": 24.5, "foreign_born": 9.2, "uninsured": 15.2, "disability": 16.8, "urban": 51.2, "college": 19.2, "veteran": 8.4, "pvi": "R+22", "top_sectors": {"Textiles & Carpet Mfg": 26.5, "Healthcare": 11.2, "Agriculture": 10.4, "Retail": 11.8}},
    "VT-Sen": {"income": 74070, "poverty": 10.5, "snap": 11.2, "medicaid": 27.5, "foreign_born": 4.8, "uninsured": 4.1, "disability": 13.5, "urban": 35.1, "college": 40.5, "veteran": 6.8, "pvi": "D+16", "top_sectors": {"Healthcare": 16.5, "Higher Education": 12.8, "Tourism": 11.5, "Specialty Ag": 8.2}},
    "ME-Sen": {"income": 68251, "poverty": 10.8, "snap": 13.5, "medicaid": 26.8, "foreign_born": 3.9, "uninsured": 6.5, "disability": 16.2, "urban": 38.7, "college": 34.0, "veteran": 9.5, "pvi": "D+2", "top_sectors": {"Shipbuilding/Defense": 14.2, "Forestry/Paper": 10.5, "Healthcare": 16.8, "Tourism": 11.2}},
    "KY-Sen": {"income": 60183, "poverty": 16.5, "snap": 15.8, "medicaid": 33.2, "foreign_born": 4.1, "uninsured": 5.6, "disability": 17.5, "urban": 58.4, "college": 25.0, "veteran": 8.1, "pvi": "R+16", "top_sectors": {"Manufacturing/Auto": 15.8, "Logistics/UPS": 11.5, "Healthcare": 14.0, "Energy/Coal": 6.8}}
}

def geocode_address_to_district(address: str) -> Optional[Dict[str, Any]]:
    """
    Call the keyless U.S. Census Bureau Geocoder API (119th Congressional Districts layer)
    to resolve a street address into its exact (state, district, matched_address).
    """
    addr = (address or "").strip()
    if len(addr) < 6:
        return None
    params = urllib.parse.urlencode({
        "address": addr,
        "benchmark": "Public_AR_Current",
        "vintage": "Current_Current",
        "layers": "119th Congressional Districts",
        "format": "json",
    })
    url = f"https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CongressCivicAnalytics/2.5"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        matches = payload.get("result", {}).get("addressMatches", [])
        if not matches:
            return None
        top = matches[0]
        geos = top.get("geographies", {})
        cd_list = geos.get("119th Congressional Districts") or []
        if not cd_list:
            for k, v in geos.items():
                if "Congressional Districts" in k and isinstance(v, list) and v:
                    cd_list = v
                    break
        if not cd_list:
            return None
        cd_entry = cd_list[0]
        state_fips = str(cd_entry.get("STATE", "")).zfill(2)
        state_abbr = STATE_FIPS_TO_ABBR.get(state_fips)
        cd_raw = next(
            (str(v) for k, v in cd_entry.items() if k.startswith("CD") and k != "CDSESSN" and str(v).isdigit()),
            None,
        ) or cd_entry.get("CDFIPS") or cd_entry.get("BASENAME") or "0"
        dist_num = int(cd_raw) if str(cd_raw).isdigit() else 0
        if dist_num == 98:  # Non-voting delegate FIPS marker
            dist_num = 0
        if not state_abbr:
            return None
        return {
            "state": state_abbr,
            "district": dist_num,
            "exact_district_match": True,
            "matched_address": top.get("matchedAddress"),
            "resolution_method": "US Census Bureau Geocoder (Exact Street District Match)",
        }
    except Exception as e:
        logger.info(f"Census geocoder lookup skipped/failed for '{addr}': {e}")
        return None


def _get_cached_or_live_acs(state_up: str, district: Optional[int], district_code: str) -> Optional[Dict[str, Any]]:
    """Return cached or live Census ACS 5-year socioeconomic stats when CENSUS_API_KEY is available."""
    global _CENSUS_ACS_CACHE
    if _CENSUS_ACS_CACHE is None:
        if _CENSUS_ACS_CACHE_PATH.exists():
            try:
                _CENSUS_ACS_CACHE = json.loads(_CENSUS_ACS_CACHE_PATH.read_text(encoding="utf-8"))
            except Exception:
                _CENSUS_ACS_CACHE = {}
        else:
            _CENSUS_ACS_CACHE = {}

    if district_code in _CENSUS_ACS_CACHE:
        return _CENSUS_ACS_CACHE[district_code]

    if not CENSUS_API_KEY:
        return None

    fips = STATE_ABBR_TO_FIPS.get(state_up)
    if not fips:
        return None

    try:
        if district is not None:
            cd_str = "00" if district == 0 else f"{district:02d}"
            geo = f"for=congressional%20district:{cd_str}&in=state:{fips}"
        else:
            geo = f"for=state:{fips}"
        # Total pop (B01003_001E), Median HH Income (B19013_001E), Poverty count (B17001_002E / B17001_001E), SNAP (B22003_002E / B22003_001E)
        vars_str = "NAME,B01003_001E,B19013_001E,B17001_002E,B17001_001E,B22003_002E,B22003_001E"
        url = f"https://api.census.gov/data/2023/acs/acs5?get={vars_str}&{geo}&key={CENSUS_API_KEY}"
        req = urllib.request.Request(url, headers={"User-Agent": "CongressCivicAnalytics/2.5"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            rows = json.loads(resp.read().decode("utf-8"))
        if len(rows) >= 2:
            hdr, vals = rows[0], rows[1]
            rec = dict(zip(hdr, vals))
            pop = int(float(rec.get("B01003_001E") or 760000))
            inc = int(float(rec.get("B19013_001E") or 70000))
            pov_num, pov_den = float(rec.get("B17001_002E") or 0), float(rec.get("B17001_001E") or 1)
            snp_num, snp_den = float(rec.get("B22003_002E") or 0), float(rec.get("B22003_001E") or 1)
            base = DISTRICT_PROFILES.get(district_code) or STATE_BASELINES.get(state_up) or {}
            merged = dict(base)
            merged.update({
                "population": pop,
                "income": inc,
                "poverty": round((pov_num / max(1.0, pov_den)) * 100.0, 1),
                "snap": round((snp_num / max(1.0, snp_den)) * 100.0, 1),
                "live_census_acs": True,
            })
            _CENSUS_ACS_CACHE[district_code] = merged
            _CENSUS_ACS_CACHE_PATH.write_text(json.dumps(_CENSUS_ACS_CACHE), encoding="utf-8")
            return merged
    except Exception as e:
        logger.debug(f"Live Census ACS fetch skipped for {district_code}: {e}")
    return None


def get_district_demographics(state: str, district: Optional[int] = None) -> ConstituentDemographics:
    """
    Retrieve Census demographics, economic drivers, safety-net usage (SNAP/Medicaid),
    and immigrant/foreign-born ratios for any US Congressional District or Senate seat.
    """
    state_up = state.upper() if state else "US"
    district_code = f"{state_up}-{district:02d}" if district is not None and district > 0 else f"{state_up}-At-Large" if district == 0 else f"{state_up}-Sen"
    
    live_data = _get_cached_or_live_acs(state_up, district, district_code)
    if live_data:
        data = live_data
    elif district_code in DISTRICT_PROFILES:
        data = DISTRICT_PROFILES[district_code]
    elif state_up in STATE_BASELINES:
        data = STATE_BASELINES[state_up]
    else:
        data = {
            "income": 74580,
            "poverty": 12.6,
            "snap": 12.5,
            "medicaid": 21.0,
            "foreign_born": 13.9,
            "uninsured": 8.5,
            "disability": 13.2,
            "urban": 80.0,
            "college": 33.7,
            "veteran": 7.0,
            "pvi": "EVEN",
            "top_sectors": {"Healthcare": 14.0, "Manufacturing": 11.0, "Tech": 8.0, "Finance": 8.0, "Agriculture": 5.0}
        }
        
    urban_pct = float(data.get("urban", 80.0))
    rural_pct = max(0.0, round(100.0 - urban_pct, 1))
    
    return ConstituentDemographics(
        district_code=district_code,
        state_name=state_up,
        population=int(data.get("population") or (760000 if district is not None else 3500000)),
        median_household_income=int(data.get("income", 74580)),
        poverty_rate_pct=float(data.get("poverty", 12.6)),
        snap_assistance_pct=float(data.get("snap", 12.5)),
        medicaid_enrolled_pct=float(data.get("medicaid", 21.0)),
        foreign_born_pct=float(data.get("foreign_born", 13.9)),
        uninsured_rate_pct=float(data.get("uninsured", 8.5)),
        disability_pct=float(data.get("disability", 13.2)),
        urban_pct=urban_pct,
        rural_pct=rural_pct,
        college_educated_pct=float(data.get("college", 33.7)),
        veteran_pct=float(data.get("veteran", 7.0)),
        top_employment_sectors=data.get("top_sectors", {}),
        partisan_lean_pvi=data.get("pvi", "EVEN")
    )
