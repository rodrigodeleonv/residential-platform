from datetime import UTC, datetime, timedelta
from decimal import Decimal

from httpx import AsyncClient

from app.modules.users.models import Role
from tests.billing.conftest import ChargeFactory, InfractionFactory, OwnerFactory
from tests.conftest import LoginAs, RoleGranter, UserFactory

TODAY = datetime.now(UTC).date()
# starts_on two days back so timezone skew (UTC vs local dates) can't matter
ACTIVE_TENANCY = {
    "starts_on": TODAY - timedelta(days=2),
    "ends_on": TODAY + timedelta(days=365),
}


def statement_url(unit_id: int) -> str:
    return f"/api/v0/units/{unit_id}/statement"


async def test_admin_creates_maintenance_charge_owner_sees_it(
    client: AsyncClient,
    create_user: UserFactory,
    login_as: LoginAs,
    make_owner: OwnerFactory,
) -> None:
    owner, unit = await make_owner()
    admin = await create_user("admin@example.com", Role.ADMIN)
    await login_as(admin)

    created = await client.post(
        f"/api/v0/units/{unit.id}/charges",
        json={"description": "Maintenance fee July", "amount": "300.00"},
    )

    assert created.status_code == 201
    body = created.json()
    assert body["kind"] == "maintenance"
    assert Decimal(body["amount"]) == Decimal("300.00")
    assert body["currency"] == "GTQ"
    assert body["paid_at"] is None

    await login_as(owner)
    statement = (await client.get(statement_url(unit.id))).json()
    assert [c["description"] for c in statement["pending"]] == ["Maintenance fee July"]
    assert Decimal(statement["pending_total"]) == Decimal("300.00")
    assert statement["paid"] == []
    assert statement["currency"] == "GTQ"


async def test_non_admin_cannot_issue_charges(
    client: AsyncClient,
    login_as: LoginAs,
    make_owner: OwnerFactory,
    create_infraction: InfractionFactory,
) -> None:
    owner, unit = await make_owner()
    infraction = await create_infraction()
    await login_as(owner)

    charge = await client.post(
        f"/api/v0/units/{unit.id}/charges",
        json={"description": "Self-billed", "amount": "1.00"},
    )
    fine = await client.post(
        f"/api/v0/units/{unit.id}/fines",
        json={"infraction_type_id": infraction.id},
    )

    assert charge.status_code == 403
    assert fine.status_code == 403


async def test_charge_amount_must_be_positive(
    client: AsyncClient,
    create_user: UserFactory,
    login_as: LoginAs,
    make_owner: OwnerFactory,
) -> None:
    _, unit = await make_owner()
    admin = await create_user("admin@example.com", Role.ADMIN)
    await login_as(admin)

    resp = await client.post(
        f"/api/v0/units/{unit.id}/charges",
        json={"description": "Zero", "amount": "0"},
    )

    assert resp.status_code == 422


async def test_fine_snapshots_catalog_values(
    client: AsyncClient,
    create_user: UserFactory,
    login_as: LoginAs,
    make_owner: OwnerFactory,
    create_infraction: InfractionFactory,
) -> None:
    _, unit = await make_owner()
    infraction = await create_infraction(
        name="Noise after hours", fine_amount=Decimal("100.00")
    )
    admin = await create_user("admin@example.com", Role.ADMIN)
    await login_as(admin)

    fined = await client.post(
        f"/api/v0/units/{unit.id}/fines",
        json={"infraction_type_id": infraction.id},
    )
    assert fined.status_code == 201
    body = fined.json()
    assert body["kind"] == "fine"
    assert body["description"] == "Noise after hours"
    assert Decimal(body["amount"]) == Decimal("100.00")
    assert body["infraction_type_id"] == infraction.id

    # raising the catalog price later must not alter the issued fine
    await client.patch(
        f"/api/v0/infractions/{infraction.id}", json={"fine_amount": "500.00"}
    )
    charges = (await client.get(f"/api/v0/charges?unit_id={unit.id}")).json()
    assert Decimal(charges[0]["amount"]) == Decimal("100.00")


async def test_fine_requires_known_active_infraction(
    client: AsyncClient,
    create_user: UserFactory,
    login_as: LoginAs,
    make_owner: OwnerFactory,
    create_infraction: InfractionFactory,
) -> None:
    _, unit = await make_owner()
    inactive = await create_infraction(name="Retired rule", is_active=False)
    admin = await create_user("admin@example.com", Role.ADMIN)
    await login_as(admin)

    unknown = await client.post(
        f"/api/v0/units/{unit.id}/fines", json={"infraction_type_id": 9999}
    )
    retired = await client.post(
        f"/api/v0/units/{unit.id}/fines", json={"infraction_type_id": inactive.id}
    )

    assert unknown.status_code == 404
    assert retired.status_code == 409


async def test_only_owners_and_admins_see_statement(
    client: AsyncClient,
    create_user: UserFactory,
    login_as: LoginAs,
    make_owner: OwnerFactory,
    grant_role: RoleGranter,
) -> None:
    owner, unit = await make_owner()
    tenant = await create_user("tenant@example.com")
    await grant_role(tenant, Role.TENANT, unit, **ACTIVE_TENANCY)
    outsider, _ = await make_owner("other@example.com", "H-2")
    admin = await create_user("admin@example.com", Role.ADMIN)

    # the tenant occupies the unit, yet the statement stays owner-only
    await login_as(tenant)
    assert (await client.get(statement_url(unit.id))).status_code == 403

    await login_as(outsider)
    assert (await client.get(statement_url(unit.id))).status_code == 403

    # the owner sees it even while renting the unit out (non-resident)
    await login_as(owner)
    assert (await client.get(statement_url(unit.id))).status_code == 200

    await login_as(admin)
    assert (await client.get(statement_url(unit.id))).status_code == 200

    client.cookies.clear()
    assert (await client.get(statement_url(unit.id))).status_code == 401


async def test_admin_marks_charge_paid(
    client: AsyncClient,
    create_user: UserFactory,
    login_as: LoginAs,
    make_owner: OwnerFactory,
    create_charge: ChargeFactory,
) -> None:
    owner, unit = await make_owner()
    charge = await create_charge(unit)
    other = await create_charge(unit, description="Still owed", amount=Decimal("50"))
    admin = await create_user("admin@example.com", Role.ADMIN)
    await login_as(admin)

    paid = await client.post(f"/api/v0/charges/{charge.id}/pay")
    assert paid.status_code == 200
    assert paid.json()["paid_at"] is not None

    repaid = await client.post(f"/api/v0/charges/{charge.id}/pay")
    assert repaid.status_code == 409
    assert (await client.post("/api/v0/charges/9999/pay")).status_code == 404

    await login_as(owner)
    statement = (await client.get(statement_url(unit.id))).json()
    assert [c["id"] for c in statement["pending"]] == [other.id]
    assert Decimal(statement["pending_total"]) == Decimal("50")
    assert [c["id"] for c in statement["paid"]] == [charge.id]


async def test_non_admin_cannot_mark_paid(
    client: AsyncClient,
    login_as: LoginAs,
    make_owner: OwnerFactory,
    create_charge: ChargeFactory,
) -> None:
    owner, unit = await make_owner()
    charge = await create_charge(unit)
    await login_as(owner)

    assert (await client.post(f"/api/v0/charges/{charge.id}/pay")).status_code == 403
