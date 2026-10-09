from datetime import date

from nn_genai.infrastructure.clients.random_user_client import RandomUserApiClient


def test_to_person_converts_datetime_to_date():
    user = {
        "name": {
            "first": "James",
            "last": "Bond",
        },
        "dob": {
            "date": "1967-10-08T08:08:14.074Z",
        },
        "nat": "GB",
        "location": {
            "country": "United Kingdom",
            "city": "London",
        },
    }

    person = RandomUserApiClient._to_person(user)

    assert person.date_of_birth == date(1967, 10, 8)
    assert person.full_name == "James Bond"
