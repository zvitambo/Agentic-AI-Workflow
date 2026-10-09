from datetime import date

from nn_genai.models.person import Person
from nn_genai.application.services.person_service import PersonService


def make_person(
    first_name: str,
    last_name: str,
    year: int,
) -> Person:
    return Person(
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date(year, 1, 1),
    )


def test_filter_people_excludes_people_born_after_2000():
    service = PersonService()

    people = [
        make_person("James", "Bond", 1967),
        make_person("Ash", "Ketchum", 1998),
        make_person("John", "Doe", 2001),
    ]

    result = service.filter_people(people)

    assert [person.full_name for person in result] == [
        "James Bond",
        "Ash Ketchum",
    ]


def test_filter_people_includes_people_born_in_2000():
    service = PersonService()

    people = [
        make_person("Person", "2000", 2000),
        make_person("Person", "2001", 2001),
    ]

    result = service.filter_people(people)

    assert [person.full_name for person in result] == [
        "Person 2000",
    ]


def test_format_people_returns_full_names():
    service = PersonService()

    people = [
        make_person("James", "Bond", 1967),
        make_person("Ash", "Ketchum", 1998),
    ]

    result = service.format_people(people)

    assert result == [
        "James Bond",
        "Ash Ketchum",
    ]
