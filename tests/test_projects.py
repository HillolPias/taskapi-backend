import pytest


async def test_create_project(client):
    response = await client.post("/projects/", json={"name": "Test Project"})

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert "id" in data


async def test_list_projects_empty(client):
    response = await client.get("/projects/")

    assert response.status_code == 200
    assert response.json() == []


async def test_list_projects_returns_created_ones(client):
    await client.post("/projects/", json={"name": "First"})
    await client.post("/projects/", json={"name": "Second"})

    response = await client.get("/projects/")

    assert response.status_code == 200
    names = [p["name"] for p in response.json()]
    assert names == ["First", "Second"]


async def test_get_nonexistent_project_returns_404(client):
    response = await client.get("/projects/999")

    assert response.status_code == 404


async def test_delete_project_cascades_to_tasks(client):
    project_resp = await client.post("/projects/", json={"name": "Will be deleted"})
    project_id = project_resp.json()["id"]

    task_resp = await client.post(
        f"/projects/{project_id}/tasks", json={"title": "Orphan-to-be"}
    )
    task_id = task_resp.json()["id"]

    delete_resp = await client.delete(f"/projects/{project_id}")
    assert delete_resp.status_code == 204

    task_check = await client.get(f"/tasks/{task_id}")
    assert task_check.status_code == 404
