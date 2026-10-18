"""Reuse the existing audit reader; do not infer progress from earned credits."""
from datetime import datetime
import math

import lehigh
from ..coursework.discovery import plain_text
from .models import DegreeProgressView, MajorProgress


def reported_number(value, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if math.isfinite(value) and value >= 0 and (maximum is None or value <= maximum) else None


def get_degree_progress():
    summary = lehigh.summarize_audit(lehigh.fetch_audit())
    try:
        audit_date = datetime.strptime(summary.get('audit_date') or '', '%m/%d/%Y').date()
    except ValueError:
        audit_date = None
    degrees = [plain_text(item.get('degree'))[:240] for item in summary['degrees']]
    return DegreeProgressView(
        degrees=list(dict.fromkeys(name for name in degrees if name)),
        completion_percent=reported_number(summary.get('degree_percent_complete'), 100),
        majors=[MajorProgress(
            name=plain_text(block.get('title'))[:240] or 'Major',
            completion_percent=reported_number(block.get('percent_complete'), 100),
        ) for block in summary['blocks'] if block.get('type') == 'MAJOR'],
        cumulative_gpa=reported_number(summary.get('gpa')),
        audit_date=audit_date,
        source_url=lehigh.AUDIT_URL,
    )
