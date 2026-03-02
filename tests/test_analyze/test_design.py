"""Tests for analyze/design.py — design phase parsing."""

from __future__ import annotations

from intake.analyze.design import parse_design


def _sample_design_json() -> dict:
    """Return a realistic LLM design response."""
    return {
        "components": ["auth-module", "api-gateway", "user-service"],
        "files_to_create": [
            {"path": "src/auth/handler.py", "description": "Auth request handler"},
            {"path": "src/auth/middleware.py", "description": "Auth middleware"},
        ],
        "files_to_modify": [
            {"path": "src/main.py", "description": "Add auth middleware registration"},
        ],
        "tech_decisions": [
            {
                "decision": "Use JWT for authentication",
                "justification": "Stateless, scalable across microservices",
                "requirement": "FR-01",
            },
        ],
        "tasks": [
            {
                "id": 1,
                "title": "Set up auth module",
                "description": "Create auth handler and middleware",
                "files": ["src/auth/handler.py", "src/auth/middleware.py"],
                "dependencies": [],
                "checks": ["pytest tests/test_auth.py -q"],
                "estimated_minutes": 15,
            },
            {
                "id": 2,
                "title": "Integrate auth middleware",
                "description": "Register middleware in main app",
                "files": ["src/main.py"],
                "dependencies": [1],
                "checks": ["pytest tests/test_main.py -q"],
                "estimated_minutes": 10,
            },
        ],
        "acceptance_checks": [
            {
                "id": "unit-tests",
                "name": "Unit tests pass",
                "type": "command",
                "command": "pytest tests/ -q",
                "required": True,
                "tags": ["test"],
            },
            {
                "id": "auth-files-exist",
                "name": "Auth module exists",
                "type": "files_exist",
                "paths": ["src/auth/handler.py"],
                "required": True,
                "tags": ["structure"],
            },
        ],
        "dependencies": ["pyjwt", "bcrypt"],
    }


class TestParseDesign:
    """Tests for parse_design()."""

    def test_parses_components(self) -> None:
        design = parse_design(_sample_design_json())
        assert len(design.components) == 3
        assert "auth-module" in design.components

    def test_parses_files_to_create(self) -> None:
        design = parse_design(_sample_design_json())
        assert len(design.files_to_create) == 2
        assert design.files_to_create[0].path == "src/auth/handler.py"
        assert design.files_to_create[0].action == "create"

    def test_parses_files_to_modify(self) -> None:
        design = parse_design(_sample_design_json())
        assert len(design.files_to_modify) == 1
        assert design.files_to_modify[0].action == "modify"

    def test_parses_tech_decisions(self) -> None:
        design = parse_design(_sample_design_json())
        assert len(design.tech_decisions) == 1
        assert "JWT" in design.tech_decisions[0].decision
        assert design.tech_decisions[0].requirement == "FR-01"

    def test_parses_tasks(self) -> None:
        design = parse_design(_sample_design_json())
        assert len(design.tasks) == 2
        assert design.tasks[0].id == 1
        assert design.tasks[0].title == "Set up auth module"
        assert design.tasks[0].dependencies == []
        assert design.tasks[1].dependencies == [1]

    def test_parses_acceptance_checks(self) -> None:
        design = parse_design(_sample_design_json())
        assert len(design.acceptance_checks) == 2
        assert design.acceptance_checks[0].type == "command"
        assert design.acceptance_checks[0].command == "pytest tests/ -q"
        assert design.acceptance_checks[1].type == "files_exist"
        assert design.acceptance_checks[1].paths == ["src/auth/handler.py"]

    def test_parses_dependencies(self) -> None:
        design = parse_design(_sample_design_json())
        assert design.dependencies == ["pyjwt", "bcrypt"]

    def test_handles_empty_json(self) -> None:
        design = parse_design({})
        assert design.components == []
        assert design.files_to_create == []
        assert design.tasks == []
        assert design.acceptance_checks == []

    def test_handles_missing_task_fields(self) -> None:
        raw = {"tasks": [{"id": 1, "title": "Do something"}]}
        design = parse_design(raw)
        assert len(design.tasks) == 1
        task = design.tasks[0]
        assert task.description == ""
        assert task.files == []
        assert task.dependencies == []
        assert task.estimated_minutes == 15
