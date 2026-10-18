"""The reported completion and GPA from one Degree Works audit snapshot."""
from datetime import date
from typing import Annotated, Literal

from pydantic import Field

from ..courses.models import Label, Model


class MajorProgress(Model):
    name: Label
    completion_percent: Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)] | None


class DegreeProgressView(Model):
    schema_version: Literal['degree_progress.v1'] = 'degree_progress.v1'
    degrees: Annotated[list[Label], Field(max_length=12)]
    completion_percent: Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)] | None
    majors: Annotated[list[MajorProgress], Field(max_length=12)]
    cumulative_gpa: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None
    audit_date: date | None
    source_url: Literal['https://dw-prod.ec.lehigh.edu/responsiveDashboard/worksheets/WEB31']
