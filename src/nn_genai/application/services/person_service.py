from nn_genai.models.person import Person


class PersonService:
    def filter_people(self, people: list[Person]) -> list[Person]:
        """
        Keep people born in or before the year 2000.

        People born after 2000 are excluded.
        """
        return [
            person
            for person in people
            if person.date_of_birth.year <= 2000
        ]

    def format_people(self, people: list[Person]) -> list[str]:
        """
        Format people as 'first_name last_name'.
        """
        return [person.full_name for person in people]
