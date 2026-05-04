from io import BytesIO
from pathlib import Path

import app.api.search as search_module


def test_category_crud_and_guard(client):
    response = client.post("/categories", json={"name": "ML"})
    assert response.status_code == 200
    category = response.json()
    assert category["name"] == "ML"

    response = client.get("/categories")
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.put(f"/categories/{category['id']}", json={"name": "AI"})
    assert response.status_code == 200
    assert response.json()["name"] == "AI"

    response = client.post(
        "/literatures",
        json={"title": "Paper", "category_id": category["id"]},
    )
    assert response.status_code == 200

    response = client.delete(f"/categories/{category['id']}")
    assert response.status_code == 400


def test_upload_parsing_and_search(client):
    payload = {
        "file": ("note.txt", BytesIO(b"Hello world from NLP"), "text/plain"),
    }
    response = client.post("/literatures/upload", files=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["content_text"]
    file_path = data["file_path"]

    response = client.get("/search", params={"q": "NLP"})
    assert response.status_code == 200
    results = response.json()
    assert len(results["items"]) == 1

    response = client.delete(f"/literatures/{data['id']}")
    assert response.status_code == 204
    assert file_path
    assert not Path(file_path).exists()


def test_agent_suggest_from_literature(client):
    content = b"My Paper Title\nAuthor: Alice\n2024\nMachine learning methods"
    payload = {
        "file": ("paper.txt", BytesIO(content), "text/plain"),
    }
    response = client.post("/literatures/upload", files=payload)
    assert response.status_code == 200
    literature = response.json()

    response = client.post(
        "/agent/suggest",
        json={"literature_id": literature["id"]},
    )
    assert response.status_code == 200
    suggestion = response.json()
    assert suggestion["title"] == "My Paper Title"
    assert suggestion["authors"] == "Author: Alice"
    assert suggestion["year"] == 2024
    assert suggestion["category_suggest"] == "Machine Learning"


def test_upload_rejects_unsupported_extension(client):
    payload = {
        "file": ("note.pdf", BytesIO(b"%PDF-1.4"), "application/pdf"),
    }
    response = client.post("/literatures/upload", files=payload)
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "bad_request"


def test_category_rename_duplicate(client):
    response = client.post("/categories", json={"name": "ML"})
    assert response.status_code == 200
    response = client.post("/categories", json={"name": "AI"})
    assert response.status_code == 200
    category = response.json()

    response = client.put(f"/categories/{category['id']}", json={"name": "ML"})
    assert response.status_code == 400


def test_search_fallback_like(client, monkeypatch):
    response = client.post(
        "/literatures",
        json={"title": "Fallback", "abstract": "NLP methods"},
    )
    assert response.status_code == 200

    def fail_fts(_db):
        raise RuntimeError("fts fail")

    monkeypatch.setattr(search_module, "ensure_fts_table", fail_fts)

    response = client.get("/search", params={"q": "NLP"})
    assert response.status_code == 200
    results = response.json()
    assert len(results["items"]) == 1


def test_import_csv_invalid_year(client):
    content = "title,year\nPaper,20xx\n"
    payload = {
        "file": ("import.csv", BytesIO(content.encode("utf-8")), "text/csv"),
    }
    response = client.post(
        "/literatures/import",
        data={"format": "csv"},
        files=payload,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["created"] == 0
    assert body["skipped"] == 1
    assert body["errors"][0]["reason"] == "Invalid year value"


def test_import_bibtex_invalid_year(client):
    content = """
@article{lit1,
  title={Test Paper},
  author={Alice},
  year={20xx}
}
"""
    payload = {
        "file": ("import.bib", BytesIO(content.encode("utf-8")), "text/plain"),
    }
    response = client.post(
        "/literatures/import",
        data={"format": "bibtex"},
        files=payload,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["created"] == 0
    assert body["skipped"] == 1
    assert body["errors"][0]["reason"] == "Invalid year value"
