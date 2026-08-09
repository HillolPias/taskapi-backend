async def test_create_task_for_project(client):
    project_resp = await client.post("/projects/", json={"name": "Task Test Project"})
    project_id = project_resp.json()["id"]

    response = await client.post(
        f"/projects/{project_id}/tasks", json={"title": "My task"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "My task"
    assert data["completed"] is False
    assert data["project_id"] == project_id


async def test_create_task_for_nonexistent_project_returns_404(client):
    response = await client.post("/projects/999/tasks", json={"title": "Orphan"})

    assert response.status_code == 404


async def test_update_task_partial_only_changes_sent_fields(client):
    project_resp = await client.post("/projects/", json={"name": "Update Test"})
    project_id = project_resp.json()["id"]
    task_resp = await client.post(
        f"/projects/{project_id}/tasks", json={"title": "Original title"}
    )
    task_id = task_resp.json()["id"]

    response = await client.patch(f"/tasks/{task_id}", json={"completed": True})

    assert response.status_code == 200
    data = response.json()
    assert data["completed"] is True
    assert data["title"] == "Original title"  # unchanged, proving partial update works


async def test_delete_task(client):
    project_resp = await client.post("/projects/", json={"name": "Delete Test"})
    project_id = project_resp.json()["id"]
    task_resp = await client.post(
        f"/projects/{project_id}/tasks", json={"title": "To delete"}
    )
    task_id = task_resp.json()["id"]

    delete_resp = await client.delete(f"/tasks/{task_id}")
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/tasks/{task_id}")
    assert get_resp.status_code == 404
