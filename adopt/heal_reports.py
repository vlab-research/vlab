"""
Report healing job entry point.

Generates respondents_over_time and cost_over_time reports for recent studies
without running optimization. Safe to run frequently as it only reads from
inference_data and recruitment_data_events tables.

Environment variables:
    REPORT_HEALING_DAYS_BACK: Number of days to look back (default: 14)
    PG_URL: PostgreSQL connection string (required)
"""

import os
from adopt.malaria import run_report_healing

DAYS_BACK = int(os.environ.get("REPORT_HEALING_DAYS_BACK", "14"))

run_report_healing(days_back=DAYS_BACK)
