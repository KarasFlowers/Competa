"""Pydantic schemas for survey and interview agents."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Survey (问卷) schemas
# ---------------------------------------------------------------------------

class QuestionType(str, Enum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    LIKERT_SCALE = "likert_scale"
    OPEN_ENDED = "open_ended"
    RANKING = "ranking"


class SurveyQuestion(BaseModel):
    """A single survey question."""

    id: str = ""
    type: QuestionType = QuestionType.OPEN_ENDED
    text: str
    options: list[str] = Field(default_factory=list)
    target_persona: str = ""
    dimension: str = ""  # e.g. "feature", "pricing", "ux", "support"


class SurveyOutput(BaseModel):
    """Structured output of the Survey Agent."""

    title: str = ""
    description: str = ""
    questions: list[SurveyQuestion] = Field(default_factory=list)
    target_audience: str = ""
    estimated_duration_min: int = 0


# ---------------------------------------------------------------------------
# Interview (访谈) schemas
# ---------------------------------------------------------------------------

class InterviewPhase(str, Enum):
    OPENING = "opening"
    CORE = "core"
    PROBING = "probing"
    CLOSING = "closing"


class InterviewQuestion(BaseModel):
    """A single interview question."""

    id: str = ""
    phase: InterviewPhase = InterviewPhase.CORE
    text: str
    follow_ups: list[str] = Field(default_factory=list)
    target_persona: str = ""
    dimension: str = ""


class InterviewGuideOutput(BaseModel):
    """Structured output of the Interview Agent."""

    title: str = ""
    target_persona: str = ""
    opening_script: str = ""
    questions: list[InterviewQuestion] = Field(default_factory=list)
    closing_script: str = ""
    estimated_duration_min: int = 0
    notes: str = ""


# ---------------------------------------------------------------------------
# Fieldwork (调研执行) schemas — synthetic respondents answer the designed
# survey + interview so findings flow back into the evidence pool.
# ---------------------------------------------------------------------------

class SurveyResponseItem(BaseModel):
    """One respondent's answer to a single survey question."""

    question_id: str = ""
    dimension: str = ""
    answer: str = ""


class SurveyResponseSet(BaseModel):
    """Aggregated survey results for one respondent segment."""

    persona: str = ""
    respondent_count: int = 0
    answers: list[SurveyResponseItem] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)


class InterviewExcerpt(BaseModel):
    """A notable quote / insight from a simulated interview session."""

    question_id: str = ""
    dimension: str = ""
    quote: str = ""
    insight: str = ""


class InterviewTranscript(BaseModel):
    """A simulated interview session with one persona."""

    persona: str = ""
    excerpts: list[InterviewExcerpt] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)


class FieldworkOutput(BaseModel):
    """Structured output of the Fieldwork Agent — simulated research results.

    These are synthetic (LLM-generated) responses grounded in the designed
    survey/interview and the personas, clearly flagged as simulated so they
    are never mistaken for real field data.
    """

    survey_results: list[SurveyResponseSet] = Field(default_factory=list)
    interview_transcripts: list[InterviewTranscript] = Field(default_factory=list)
    summary: str = ""
