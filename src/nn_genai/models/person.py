from datetime import date

from pydantic import BaseModel
from pydantic import BaseModel

class Person(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    nationality: str | None = None
    country: str | None = None
    city: str | None = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
