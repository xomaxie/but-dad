from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(slots=True)
class Critique:
    claim: str
    recommendation: str
    sources: List[str] = field(default_factory=list)


@dataclass(slots=True)
class SpecDraft:
    version: int
    content: str
    rationale: List[str] = field(default_factory=list)


@dataclass(slots=True)
class LoopConfig:
    max_writer_turns: int = 6
    max_coach_turns: int = 6


@dataclass(slots=True)
class SpecLoopState:
    config: LoopConfig = field(default_factory=LoopConfig)
    drafts: List[SpecDraft] = field(default_factory=list)
    critiques: List[Critique] = field(default_factory=list)

    def add_draft(self, content: str, rationale: List[str] | None = None) -> SpecDraft:
        draft = SpecDraft(version=len(self.drafts) + 1, content=content, rationale=rationale or [])
        self.drafts.append(draft)
        return draft

    def add_critique(self, claim: str, recommendation: str, sources: List[str] | None = None) -> Critique:
        critique = Critique(claim=claim, recommendation=recommendation, sources=sources or [])
        self.critiques.append(critique)
        return critique

    @property
    def writer_turns_used(self) -> int:
        return len(self.drafts)

    @property
    def coach_turns_used(self) -> int:
        return len(self.critiques)

    def can_continue(self) -> bool:
        return (
            self.writer_turns_used < self.config.max_writer_turns
            and self.coach_turns_used < self.config.max_coach_turns
        )
