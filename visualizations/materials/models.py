"""Selections reference real course-module IDs; the server supplies all links."""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from ..courses.models import Label, Model, Notice, PositiveID


class MaterialSelection(Model):
    title: Label
    module_ids: Annotated[list[PositiveID], Field(min_length=1, max_length=20)]


Selections = Annotated[list[MaterialSelection], Field(min_length=1, max_length=6)]


class MaterialsQuery(Model):
    course_id: PositiveID
    groups: Selections

    @model_validator(mode='after')
    def unique_modules(self):
        ids = [module_id for group in self.groups for module_id in group.module_ids]
        if len(ids) != len(set(ids)):
            raise ValueError('Select each course material only once.')
        return self


class Material(Model):
    module_id: PositiveID
    name: Label
    section: Label
    source_url: Annotated[str, Field(max_length=2048)]
    filename: Label | None = None
    size: Annotated[int, Field(ge=0)] | None = None
    download_url: Annotated[str, Field(max_length=2048)] | None = None


class MaterialGroup(Model):
    title: Label
    items: Annotated[list[Material], Field(max_length=60)]
    notice: Notice | None = None


class MaterialsView(Model):
    schema_version: Literal['materials.v1'] = 'materials.v1'
    course_id: PositiveID
    course_name: Label
    site_url: Annotated[str, Field(max_length=2048)]
    groups: Annotated[list[MaterialGroup], Field(max_length=6)]
    coverage: Notice = 'Selected course materials, not verified exam coverage. Downloads use your CourseSite browser sign-in.'
