"""Syllabus-backed inputs and output for the separate grade-target tool."""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from ..courses.models import Label, Model, Notice, PositiveID
from ..gradebook.models import GradeRef, Syllabus, URL

Percent = Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
Weight = Annotated[float, Field(gt=0, le=100, allow_inf_nan=False)]


class WeightedWork(Model):
    name: Label
    weight: Weight
    grade_ref: GradeRef | None = None


class GradingPlan(Model):
    syllabus_module_id: PositiveID
    evidence: Annotated[str, Field(min_length=20, max_length=8000)]
    explanation: Notice
    assumptions: Annotated[list[Notice], Field(max_length=4)] = Field(default_factory=list)
    work: Annotated[list[WeightedWork], Field(min_length=1, max_length=80)]

    @model_validator(mode='after')
    def complete_weights(self):
        if abs(sum(item.weight for item in self.work) - 100) > 0.001:
            raise ValueError('Final-course weights must add up to 100%.')
        refs = [item.grade_ref for item in self.work if item.grade_ref]
        if len(refs) != len(set(refs)):
            raise ValueError('Use each grade only once in the projection.')
        if len({item.name.casefold() for item in self.work}) != len(self.work):
            raise ValueError('Give each assessment or remaining-work group a distinct name.')
        return self


class ProjectedWork(WeightedWork):
    percent: Percent | None = None


class Projection(Model):
    source_url: URL
    explanation: Notice
    assumptions: Annotated[list[Notice], Field(max_length=4)] = Field(default_factory=list)
    work: Annotated[list[ProjectedWork], Field(min_length=1, max_length=80)]
    target: Percent = 90


class GradeTargetView(Model):
    schema_version: Literal['grade_target.v1'] = 'grade_target.v1'
    course_id: PositiveID
    course_name: Label
    site_url: URL
    syllabi: Annotated[list[Syllabus], Field(max_length=6)]
    projection: Projection | None = None
    projection_notice: Notice | None = None
