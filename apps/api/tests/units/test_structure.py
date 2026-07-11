from httpx import AsyncClient

from app.modules.users.models import Role
from tests.conftest import LoginAs, UserFactory
from tests.utils import API


async def _admin(create_user: UserFactory, login_as: LoginAs) -> None:
    await login_as(await create_user("admin@example.com", Role.ADMIN))


async def test_structure_is_admin_only(
    client: AsyncClient, create_user: UserFactory, login_as: LoginAs
) -> None:
    await login_as(await create_user("resident@example.com"))

    for call in (
        client.post(f"{API}/buildings", json={"name": "A"}),
        client.post(f"{API}/units", json={"kind": "house", "number": "H-1"}),
        client.post(f"{API}/visitor-parking-spots", json={"number": "V-1"}),
        client.get(f"{API}/units"),
    ):
        assert (await call).status_code == 403


async def test_admin_creates_building_apartment_and_house(
    client: AsyncClient, create_user: UserFactory, login_as: LoginAs
) -> None:
    await _admin(create_user, login_as)

    building = (
        await client.post(f"{API}/buildings", json={"name": "Building A"})
    ).json()
    apartment = await client.post(
        f"{API}/units",
        json={
            "kind": "apartment",
            "building_id": building["id"],
            "floor": 3,
            "number": "301",
        },
    )
    house = await client.post(f"{API}/units", json={"kind": "house", "number": "H-7"})

    assert apartment.status_code == 201
    assert house.status_code == 201
    units = (await client.get(f"{API}/units")).json()
    assert [(u["kind"], u["number"]) for u in units] == [
        ("apartment", "301"),
        ("house", "H-7"),
    ]


async def test_apartment_requires_building_and_floor(
    client: AsyncClient, create_user: UserFactory, login_as: LoginAs
) -> None:
    await _admin(create_user, login_as)

    response = await client.post(
        f"{API}/units", json={"kind": "apartment", "number": "101"}
    )

    assert response.status_code == 422


async def test_house_cannot_have_building_or_floor(
    client: AsyncClient, create_user: UserFactory, login_as: LoginAs
) -> None:
    await _admin(create_user, login_as)

    response = await client.post(
        f"{API}/units", json={"kind": "house", "floor": 1, "number": "H-1"}
    )

    assert response.status_code == 422


async def test_unknown_building_is_rejected(
    client: AsyncClient, create_user: UserFactory, login_as: LoginAs
) -> None:
    await _admin(create_user, login_as)

    response = await client.post(
        f"{API}/units",
        json={"kind": "apartment", "building_id": 999, "floor": 1, "number": "101"},
    )

    assert response.status_code == 404


async def test_duplicate_unit_number_in_same_building(
    client: AsyncClient, create_user: UserFactory, login_as: LoginAs
) -> None:
    await _admin(create_user, login_as)
    building = (await client.post(f"{API}/buildings", json={"name": "B"})).json()
    payload = {
        "kind": "apartment",
        "building_id": building["id"],
        "floor": 1,
        "number": "101",
    }

    assert (await client.post(f"{API}/units", json=payload)).status_code == 201
    assert (await client.post(f"{API}/units", json=payload)).status_code == 409


async def test_duplicate_house_number(
    client: AsyncClient, create_user: UserFactory, login_as: LoginAs
) -> None:
    await _admin(create_user, login_as)
    payload = {"kind": "house", "number": "H-1"}

    assert (await client.post(f"{API}/units", json=payload)).status_code == 201
    assert (await client.post(f"{API}/units", json=payload)).status_code == 409


async def test_visitor_parking_spots(
    client: AsyncClient, create_user: UserFactory, login_as: LoginAs
) -> None:
    await _admin(create_user, login_as)

    assert (
        await client.post(f"{API}/visitor-parking-spots", json={"number": "V-1"})
    ).status_code == 201
    assert (
        await client.post(f"{API}/visitor-parking-spots", json={"number": "V-1"})
    ).status_code == 409
    spots = (await client.get(f"{API}/visitor-parking-spots")).json()
    assert [s["number"] for s in spots] == ["V-1"]
