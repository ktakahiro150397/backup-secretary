import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOOGLE_API_PATH = ROOT / "scripts" / "google_api.py"
SETUP_PATH = ROOT / "scripts" / "setup.py"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_setup_requests_google_tasks_scope():
    setup = load_module(SETUP_PATH, "google_setup_for_tasks_test")
    assert "https://www.googleapis.com/auth/tasks" in setup.SCOPES


class FakeRequest:
    def __init__(self, result=None):
        self.result = result or {}

    def execute(self):
        return self.result


class FakeTaskListsResource:
    def list(self, maxResults):
        assert maxResults == 10
        return FakeRequest({"items": [{"id": "@default", "title": "My Tasks", "updated": "2026-04-28T00:00:00Z"}]})


class FakeTasksResource:
    def __init__(self):
        self.insert_body = None
        self.patch_body = None
        self.deleted = None

    def list(self, **kwargs):
        assert kwargs == {"tasklist": "@default", "maxResults": 5, "showCompleted": False, "showHidden": False}
        return FakeRequest({
            "items": [{
                "id": "task-1",
                "title": "Buy milk",
                "notes": "low fat",
                "status": "needsAction",
                "due": "2026-04-30T00:00:00.000Z",
                "updated": "2026-04-28T00:00:00Z",
            }]
        })

    def insert(self, tasklist, body):
        assert tasklist == "@default"
        self.insert_body = body
        return FakeRequest({"id": "task-2", **body, "status": "needsAction"})

    def patch(self, tasklist, task, body):
        assert tasklist == "@default"
        assert task == "task-1"
        self.patch_body = body
        return FakeRequest({"id": task, "title": "Buy milk", **body})

    def delete(self, tasklist, task):
        self.deleted = (tasklist, task)
        return FakeRequest({})


class FakeTasksService:
    def __init__(self):
        self.tasks_resource = FakeTasksResource()

    def tasklists(self):
        return FakeTaskListsResource()

    def tasks(self):
        return self.tasks_resource


def test_tasks_lists_outputs_tasklists(monkeypatch, capsys):
    api = load_module(GOOGLE_API_PATH, "google_api_tasks_lists_test")
    fake = FakeTasksService()
    monkeypatch.setattr(api, "_gws_binary", lambda: None)
    monkeypatch.setattr(api, "build_service", lambda api_name, version: fake)

    api.tasks_lists(argparse.Namespace(max=10))

    output = json.loads(capsys.readouterr().out)
    assert output == [{"id": "@default", "title": "My Tasks", "updated": "2026-04-28T00:00:00Z"}]


def test_tasks_list_outputs_tasks(monkeypatch, capsys):
    api = load_module(GOOGLE_API_PATH, "google_api_tasks_list_test")
    fake = FakeTasksService()
    monkeypatch.setattr(api, "_gws_binary", lambda: None)
    monkeypatch.setattr(api, "build_service", lambda api_name, version: fake)

    api.tasks_list(argparse.Namespace(tasklist="@default", max=5, show_completed=False, show_hidden=False))

    output = json.loads(capsys.readouterr().out)
    assert output == [{
        "id": "task-1",
        "title": "Buy milk",
        "notes": "low fat",
        "status": "needsAction",
        "due": "2026-04-30T00:00:00.000Z",
        "completed": "",
        "updated": "2026-04-28T00:00:00Z",
        "parent": "",
        "position": "",
    }]


def test_tasks_create_sends_title_notes_due(monkeypatch, capsys):
    api = load_module(GOOGLE_API_PATH, "google_api_tasks_create_test")
    fake = FakeTasksService()
    monkeypatch.setattr(api, "_gws_binary", lambda: None)
    monkeypatch.setattr(api, "build_service", lambda api_name, version: fake)

    api.tasks_create(argparse.Namespace(tasklist="@default", title="Buy milk", notes="low fat", due="2026-04-30"))

    assert fake.tasks_resource.insert_body == {
        "title": "Buy milk",
        "notes": "low fat",
        "due": "2026-04-30T00:00:00.000Z",
    }
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "created"
    assert output["id"] == "task-2"
    assert output["title"] == "Buy milk"


def test_tasks_complete_marks_task_completed(monkeypatch, capsys):
    api = load_module(GOOGLE_API_PATH, "google_api_tasks_complete_test")
    fake = FakeTasksService()
    monkeypatch.setattr(api, "_gws_binary", lambda: None)
    monkeypatch.setattr(api, "build_service", lambda api_name, version: fake)

    api.tasks_complete(argparse.Namespace(tasklist="@default", task_id="task-1"))

    assert fake.tasks_resource.patch_body["status"] == "completed"
    assert fake.tasks_resource.patch_body["completed"].endswith("Z")
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "completed"
    assert output["id"] == "task-1"


def test_tasks_delete_outputs_deleted(monkeypatch, capsys):
    api = load_module(GOOGLE_API_PATH, "google_api_tasks_delete_test")
    fake = FakeTasksService()
    monkeypatch.setattr(api, "_gws_binary", lambda: None)
    monkeypatch.setattr(api, "build_service", lambda api_name, version: fake)

    api.tasks_delete(argparse.Namespace(tasklist="@default", task_id="task-1"))

    assert fake.tasks_resource.deleted == ("@default", "task-1")
    assert json.loads(capsys.readouterr().out) == {"status": "deleted", "taskId": "task-1"}
