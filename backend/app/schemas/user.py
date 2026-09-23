from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    nif: Optional[str] = None
    cuota_autonomos_mensual: float = Field(default=0.0, ge=0, le=100000)


class UserProfileOut(UserProfileUpdate):
    model_config = ConfigDict(from_attributes=True)

    email: str
