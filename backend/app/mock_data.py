"""Synthetic SD Worx-style knowledge landscape.

Everything here is fictional. No real employees, customers or policies.
Dates are expressed as "days ago" relative to server start so the demo
never goes stale.
"""

from __future__ import annotations

COUNTRIES = {
    "BE": "Belgium",
    "NL": "Netherlands",
    "FR": "France",
    "DE": "Germany",
    "UK": "United Kingdom",
}

# role: "consultant" can read + flag, "expert" can also verify, "admin" can do everything
EMPLOYEES = [
    {"id": "emp-anna", "name": "Anna Peeters", "role": "expert", "countries": ["BE"], "active": True,
     "expertise": ["holiday pay", "payroll", "joint committee", "meal vouchers", "sick leave"]},
    {"id": "emp-bram", "name": "Bram de Vries", "role": "expert", "countries": ["NL"], "active": True,
     "expertise": ["holiday allowance", "payroll", "pension"]},
    {"id": "emp-claire", "name": "Claire Martin", "role": "expert", "countries": ["FR"], "active": True,
     "expertise": ["meal vouchers", "overtime", "rtt"]},
    {"id": "emp-dirk", "name": "Dirk Schneider", "role": "expert", "countries": ["DE"], "active": True,
     "expertise": ["sick leave", "payroll", "works council"]},
    {"id": "emp-emma", "name": "Emma Clarke", "role": "expert", "countries": ["UK"], "active": True,
     "expertise": ["statutory sick pay", "pension auto-enrolment"]},
    {"id": "emp-frank", "name": "Frank Janssens", "role": "expert", "countries": ["BE"], "active": False,
     "expertise": ["remote work allowance", "company cars"]},  # left the company -> orphaned docs
    {"id": "emp-greet", "name": "Greet Maes", "role": "consultant", "countries": ["BE"], "active": True,
     "expertise": ["client onboarding"]},
    {"id": "emp-hugo", "name": "Hugo Lambert", "role": "consultant", "countries": ["BE", "FR"], "active": True,
     "expertise": ["cross-border payroll"]},
    {"id": "emp-ines", "name": "Ines Admin", "role": "admin", "countries": list(COUNTRIES), "active": True,
     "expertise": ["knowledge management"]},
]

# verified_days_ago: None means never verified
DOCUMENTS = [
    # --- The "real stories, real friction" scenario: Belgian holiday pay ---
    {"id": "doc-be-holiday-2026", "title": "Belgian double holiday pay calculation (2026 update)",
     "tags": ["holiday pay", "double holiday pay", "vakantiegeld", "payroll", "belgium"],
     "countries": ["BE"], "author": "emp-anna", "verified_days_ago": 12, "updated_days_ago": 12,
     "summary": "Double holiday pay for white-collar workers equals 92% of monthly gross salary, "
                "paid in May or on exit. Includes the 2026 social-security ceiling changes."},
    {"id": "doc-be-holiday-legacy", "title": "Holiday pay procedure - legacy handover notes",
     "tags": ["holiday pay", "vakantiegeld", "payroll", "handover"],
     "countries": ["BE"], "author": None, "verified_days_ago": 840, "updated_days_ago": 900,
     "summary": "Old handover notes describing a 85% double holiday pay rule and manual exit calculation."},
    {"id": "doc-nl-holiday", "title": "Holiday allowance (vakantiegeld) - Netherlands",
     "tags": ["holiday pay", "holiday allowance", "vakantiegeld", "payroll"],
     "countries": ["NL"], "author": "emp-bram", "verified_days_ago": 40, "updated_days_ago": 40,
     "summary": "Dutch holiday allowance is at least 8% of annual gross salary, usually paid in May."},
    # --- Remote work: owner left the company ---
    {"id": "doc-be-remote", "title": "Remote work allowance - Belgian tax-free ceiling",
     "tags": ["remote work", "home office", "allowance", "belgium"],
     "countries": ["BE"], "author": "emp-frank", "verified_days_ago": 410, "updated_days_ago": 410,
     "summary": "Tax-free monthly home-office allowance and the conditions for structural remote work."},
    # --- Other countries ---
    {"id": "doc-fr-meal", "title": "Titres-restaurant: employer contribution limits",
     "tags": ["meal vouchers", "benefits", "france"],
     "countries": ["FR"], "author": "emp-claire", "verified_days_ago": 30, "updated_days_ago": 30,
     "summary": "Employer share must be between 50% and 60% of the voucher value, within the exemption cap."},
    {"id": "doc-be-meal", "title": "Meal vouchers - Belgian maximum face value",
     "tags": ["meal vouchers", "benefits", "belgium"],
     "countries": ["BE"], "author": "emp-anna", "verified_days_ago": 95, "updated_days_ago": 95,
     "summary": "Maximum face value, minimum employee contribution and electronic delivery rules."},
    {"id": "doc-de-sick", "title": "Entgeltfortzahlung: continued pay during sick leave",
     "tags": ["sick leave", "payroll", "germany"],
     "countries": ["DE"], "author": "emp-dirk", "verified_days_ago": 60, "updated_days_ago": 60,
     "summary": "Employer pays 100% for up to six weeks, then statutory health insurance takes over."},
    {"id": "doc-uk-ssp", "title": "Statutory Sick Pay (SSP) quick reference",
     "tags": ["sick leave", "statutory sick pay", "payroll", "uk"],
     "countries": ["UK"], "author": "emp-emma", "verified_days_ago": 200, "updated_days_ago": 200,
     "summary": "Eligibility, waiting days and weekly rate for Statutory Sick Pay."},
    {"id": "doc-be-sick", "title": "Guaranteed salary during sick leave - Belgium",
     "tags": ["sick leave", "guaranteed salary", "payroll", "belgium"],
     "countries": ["BE"], "author": "emp-anna", "verified_days_ago": 150, "updated_days_ago": 150,
     "summary": "First month of incapacity is paid by the employer (guaranteed salary) for white-collar workers."},
    {"id": "doc-crossborder", "title": "Cross-border workers BE/FR: which payroll applies",
     "tags": ["cross-border", "payroll", "social security"],
     "countries": ["BE", "FR"], "author": "emp-hugo", "verified_days_ago": 70, "updated_days_ago": 70,
     "summary": "Determining the competent social-security state for employees working in BE and FR."},
]

# Teams chats that contradict documents
TEAMS_CHATS = [
    {"id": "chat-be-holiday-1", "channel": "#payroll-be", "author": "emp-greet", "days_ago": 3,
     "countries": ["BE"], "contradicts": "doc-be-holiday-legacy",
     "text": "Careful: the 85% rule in the legacy notes is outdated, the client got a correction last month."},
    {"id": "chat-be-remote-1", "channel": "#tax-be", "author": "emp-anna", "days_ago": 20,
     "countries": ["BE"], "contradicts": "doc-be-remote",
     "text": "The home-office ceiling was indexed again, the amount in that doc is no longer correct."},
    {"id": "chat-nl-holiday-1", "channel": "#payroll-nl", "author": "emp-bram", "days_ago": 5,
     "countries": ["NL"], "contradicts": None,
     "text": "Reminder: NL holiday allowance runs in the May payroll."},
]

# Expert endorsements (an expert vouched for a doc in a review)
ENDORSEMENTS = [
    ("emp-hugo", "doc-be-holiday-2026"),
    ("emp-greet", "doc-be-holiday-2026"),
    ("emp-anna", "doc-be-sick"),
    ("emp-hugo", "doc-crossborder"),
    ("emp-claire", "doc-crossborder"),
]
