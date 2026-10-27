"""Helpers shared by the members and access-boundary tests (FR-13 … FR-20)."""

from http import HTTPStatus
from typing import Any

from httpx import AsyncClient, Response

from tests.factories import API, Account, Factories

BORIS_EMAIL = "boris@romashka.test"
DINA_EMAIL = "dina@romashka.test"
VERA_EMAIL = "vera@lyutik.test"
LAST_ADMINISTRATOR = "В организации должен остаться хотя бы один активный администратор"
CANNOT_DEACTIVATE_SELF = "Нельзя отключить свою учётную запись"
MEMBER_INACTIVE = "Сначала включите учётную запись участника"
ACCOUNT_DISABLED = "Учётная запись отключена. Обратитесь к администратору организации"
NOT_FOUND = "Не найдено"
UNKNOWN_ID = "00000000-0000-0000-0000-000000000001"


async def list_members(admin: AsyncClient) -> list[dict[str, Any]]:
    """The items of GET /members that must succeed."""
    response = await admin.get(f"{API}/members")
    assert response.status_code == HTTPStatus.OK
    return response.json()["items"]


async def member_of(admin: AsyncClient, user_id: str) -> dict[str, Any]:
    """The row of one member in GET /members."""
    return next(m for m in await list_members(admin) if m["id"] == user_id)


async def deactivate(client: AsyncClient, user_id: str) -> Response:
    """POST /members/{id}/deactivate."""
    return await client.post(f"{API}/members/{user_id}/deactivate")


async def reactivate(client: AsyncClient, user_id: str) -> Response:
    """POST /members/{id}/reactivate."""
    return await client.post(f"{API}/members/{user_id}/reactivate")


async def set_role(client: AsyncClient, user_id: str, role: str) -> Response:
    """PUT /members/{id}/role."""
    return await client.put(f"{API}/members/{user_id}/role", json={"role": role})


def assert_error(response: Response, status: int, code: str, message: str) -> None:
    """The response is the documented error: status, code and the exact Russian message."""
    assert response.status_code == status
    assert response.json() == {"error": {"code": code, "message": message}}


async def romashka_team(
    factories: Factories,
) -> tuple[AsyncClient, Account, AsyncClient, Account]:
    """Анна (administrator) and Борис (employee) of «ООО Ромашка», both signed in."""
    anna = await factories.confirmed_admin()
    anna_client = await factories.signed_in(anna)
    boris = await factories.employee(anna_client, email=BORIS_EMAIL)
    return anna_client, anna, await factories.signed_in(boris), boris


async def two_administrators(
    factories: Factories,
) -> tuple[AsyncClient, Account, AsyncClient, Account]:
    """Анна and Борис, both administrators of «ООО Ромашка», each on a signed-in client."""
    anna_client, anna, boris_client, boris = await romashka_team(factories)
    promoted = await set_role(anna_client, boris.user_id, "administrator")
    assert promoted.status_code == HTTPStatus.OK
    return anna_client, anna, boris_client, boris
