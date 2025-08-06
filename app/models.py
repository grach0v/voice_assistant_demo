from pydantic import BaseModel


class VerifyRequest(BaseModel):
    postal_code: str
    tracking_id: str


class UpdateDateRequest(BaseModel):
    tracking_id: str
    new_date: str


class FinishCallRequest(BaseModel):
    tracking_id: str
