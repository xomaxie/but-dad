from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


class TurnLimitError(ValueError):
    pass


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
        self._ensure_writer_capacity()
        draft = SpecDraft(version=len(self.drafts) + 1, content=content, rationale=rationale or [])
        self.drafts.append(draft)
        return draft

    def add_critique(self, claim: str, recommendation: str, sources: List[str] | None = None) -> Critique:
        self._ensure_coach_capacity()
        critique = Critique(claim=claim, recommendation=recommendation, sources=sources or [])
        self.critiques.append(critique)
        return critique

    @property
    def writer_turns_used(self) -> int:
        return len(self.drafts)

    @property
    def coach_turns_used(self) -> int:
        return len(self.critiques)

    @property
    def remaining_writer_turns(self) -> int:
        return self.config.max_writer_turns - self.writer_turns_used

    @property
    def remaining_coach_turns(self) -> int:
        return self.config.max_coach_turns - self.coach_turns_used

    def can_continue(self) -> bool:
        return self.remaining_writer_turns > 0 and self.remaining_coach_turns > 0

    def build_final_spec(self, title: str = "But Dad Spec") -> str:
        lines = [
            f"# {title}",
            "",
            "## Loop summary",
            f"- Writer turns: {self.writer_turns_used}/{self.config.max_writer_turns}",
            f"- Coach turns: {self.coach_turns_used}/{self.config.max_coach_turns}",
            "",
            "## Current spec",
        ]

        if self.drafts:
            lines.extend([self.drafts[-1].content, ""])
        else:
            lines.extend(["_No draft has been recorded yet._", ""])

        lines.extend(["## Draft history", ""])
        if not self.drafts:
            lines.extend(["_No drafts recorded._", ""])
        else:
            for draft in self.drafts:
                lines.extend([f"### Draft {draft.version}", "", draft.content, ""])
                if draft.rationale:
                    lines.append("#### Rationale")
                    lines.extend(f"- {item}" for item in draft.rationale)
                    lines.append("")

        lines.extend(["## Coach critiques", ""])
        if not self.critiques:
            lines.extend(["_No critiques recorded._", ""])
        else:
            for index, critique in enumerate(self.critiques, start=1):
                lines.extend(
                    [
                        f"### Critique {index}",
                        "",
                        f"- Claim: {critique.claim}",
                        f"- Recommendation: {critique.recommendation}",
                    ]
                )
                if critique.sources:
                    lines.append("- Sources:")
                    lines.extend(f"  - {source}" for source in critique.sources)
                lines.append("")

        lines.extend(["## Source appendix", ""])
        sources = self._unique_sources()
        if sources:
            lines.extend(f"{index}. {source}" for index, source in enumerate(sources, start=1))
        else:
            lines.append("_No sources captured._")

        lines.append("")
        return "\n".join(lines)

    def _ensure_writer_capacity(self) -> None:
        if self.writer_turns_used >= self.config.max_writer_turns:
            raise TurnLimitError("writer turn limit reached")

    def _ensure_coach_capacity(self) -> None:
        if self.coach_turns_used >= self.config.max_coach_turns:
            raise TurnLimitError("coach turn limit reached")

    def _unique_sources(self) -> List[str]:
        seen: set[str] = set()
        ordered_sources: List[str] = []
        for critique in self.critiques:
            for source in critique.sources:
                if source in seen:
                    continue
                seen.add(source)
                ordered_sources.append(source)
        return ordered_sources
