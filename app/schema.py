from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class Provider(BaseModel):
    id: str
    name: str
    mu_L_per_kWh: float
    sigma_L_per_kWh: float = Field(ge=0)
    mu_kg_per_kWh: float
    sigma_kg_per_kWh: float = Field(ge=0)


class ModelConfig(BaseModel):
    id: str
    provider_id: str
    match_prefixes: list[str]
    input: float = Field(ge=0)
    output: float = Field(ge=0)
    cache_read: float = Field(ge=0)
    cache_write: float = Field(ge=0)
    mu_kWh_per_usd: float
    sigma_kWh_per_usd: float = Field(ge=0)

    @field_validator("match_prefixes")
    @classmethod
    def prefixes_non_empty(cls, value: list[str]) -> list[str]:
        cleaned = [p for p in value if p]
        if not cleaned:
            raise ValueError("match_prefixes ne peut pas être vide")
        return cleaned


class Settings(BaseModel):
    providers: list[Provider]
    models: list[ModelConfig]

    def provider_by_id(self) -> dict[str, Provider]:
        return {p.id: p for p in self.providers}

    def model_by_id(self) -> dict[str, ModelConfig]:
        return {m.id: m for m in self.models}
