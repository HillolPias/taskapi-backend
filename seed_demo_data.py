# seed_demo_data.py
import httpx
import time

BASE_URL = "https://taskapi-backend.onrender.com"

DEMO_DATA = [
    {
        "name": "Website Redesign",
        "tasks": [
            ("Wireframe homepage layout", True),
            ("Choose new color palette and typography", True),
            ("Implement responsive navigation bar", False),
            ("Write new landing page copy", False),
            ("Cross-browser QA testing", False),
        ],
    },
    {
        "name": "Q3 Marketing Campaign",
        "tasks": [
            ("Draft email newsletter", True),
            ("Schedule social media posts", True),
            ("Analyze competitor campaigns", True),
            ("Design banner ad creatives", False),
            ("Finalize budget with finance team", False),
        ],
    },
    {
        "name": "Mobile App Launch",
        "tasks": [
            ("Fix onboarding flow crash bug", True),
            ("Set up App Store listing", False),
            ("Write release notes", False),
            ("Submit build for App Store review", False),
        ],
    },
    {
        "name": "Client Onboarding Portal",
        "tasks": [
            ("Design database schema", True),
            ("Build authentication flow", True),
            ("Deploy staging environment", True),
            ("Create admin dashboard", False),
            ("Write API documentation", False),
        ],
    },
]


def request_json(client: httpx.Client, method: str, url: str, **kwargs):
    """Make a request and print debugging info if the response isn't valid JSON."""
    response = client.request(method, url, **kwargs)
    print(f"{method} {url} -> {response.status_code}")
    if not response.text:
        raise RuntimeError(
            f"Empty response body from {method} {url} (status {response.status_code})"
        )
    try:
        return response.json()
    except Exception:
        print(f"Raw response body: {response.text[:500]}")
        raise


def main():
    client = httpx.Client(base_url=BASE_URL, timeout=60)

    # Wake up the server first (Render free tier sleeps after inactivity)
    print("Pinging /health to wake up the server (may take up to a minute)...")
    for attempt in range(6):
        try:
            r = client.get("/health", timeout=60)
            if r.status_code == 200:
                print("Server is awake.")
                break
        except httpx.RequestError as e:
            print(f"Attempt {attempt + 1}: {e}, retrying in 10s...")
        time.sleep(10)
    else:
        raise RuntimeError("Server never woke up after multiple attempts.")

    # Clear out any existing placeholder projects
    existing = request_json(client, "GET", "/projects/")
    for project in existing:
        client.delete(f"/projects/{project['id']}")
        print(f"Deleted existing project: {project['name']}")

    # Create fresh demo data
    for project_data in DEMO_DATA:
        project = request_json(
            client, "POST", "/projects/", json={"name": project_data["name"]}
        )
        print(f"Created project: {project['name']} (id={project['id']})")

        for title, completed in project_data["tasks"]:
            task = request_json(
                client,
                "POST",
                f"/projects/{project['id']}/tasks",
                json={"title": title},
            )
            if completed:
                client.patch(f"/tasks/{task['id']}", json={"completed": True})
            print(f"  - {title} ({'done' if completed else 'pending'})")

    # Rebuild the RAG index so chat/rag and chat/agent reflect the new data
    reindex_result = request_json(client, "POST", "/chat/reindex")
    print(f"\nReindexed {reindex_result['indexed_documents']} documents for RAG.")


if __name__ == "__main__":
    main()
