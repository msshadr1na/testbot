from pydantic import BaseModel

class UserName(BaseModel):
    first_name: str | None = None
    last_name: str | None = None