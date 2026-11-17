from __future__ import annotations

from pydantic import BaseModel, Field


class Scene(BaseModel):
    number: int
    on_screen_text: str
    narration: str
    visual_prompt: str
    duration_seconds: float = 4.0


class ReelPackage(BaseModel):
    niche: str
    title: str
    hook: str
    language: str = "en"
    scenes: list[Scene] = Field(default_factory=list)
    caption: str
    hashtags: list[str] = Field(default_factory=list)
    cta: str = "Follow for more stories."

    @property
    def full_narration(self) -> str:
        parts = [s.narration.strip() for s in self.scenes if s.narration.strip()]
        if self.cta and self.cta not in " ".join(parts):
            parts.append(self.cta)
        return " ".join(parts)
