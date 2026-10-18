from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApplicationStatus(StrEnum):
    DRAFT = 'draft'
    SUBMITTED = 'submitted'
    NEEDS_CORRECTION = 'needs_correction'
    RESUBMITTED = 'resubmitted'
    APPROVED = 'approved'
    REJECTED = 'rejected'


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    decision: Literal['approved', 'rejected', 'needs_correction']
    note: str = Field(default='', max_length=4000)
    expected_version: int = Field(ge=0)


class TransitionEvent(BaseModel):
    actor_user_id: str
    application_id: str
    action: str
    before: ApplicationStatus
    after: ApplicationStatus
    note: str
    created_at: datetime
