"""Governance tests — the Constitution as executable checks.

These cover Constitution Art. 2 (MIT license + permissive-only runtime chain) and
Art. 3 (settled naming). They are not tied to a REQ id: they guard the articles
themselves, which every REQ-bearing test presupposes.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / "pyproject.toml"

# Constitution Art. 2 as amended (A-2026-08-08-01).
PERMITTED_RUNTIME_LICENSES = {
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
}

# Art. 3: these names must never appear anywhere in code, docs, or metadata.
FORBIDDEN_NAMES = ("reflex-flow", "reflex-xyflow", "reflex_flow", "reflex_xyflow")


@pytest.fixture(scope="module")
def pyproject() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


# --- Art. 2: license and dependency chain ---------------------------------


def test_project_declares_mit_license(pyproject: dict) -> None:
    """Art. 2: `license = "MIT"` in pyproject."""
    assert pyproject["project"]["license"] == "MIT"


def test_project_declares_mit_classifier(pyproject: dict) -> None:
    """Art. 2: the OSI MIT classifier is present."""
    assert "License :: OSI Approved :: MIT License" in pyproject["project"]["classifiers"]


def test_license_file_is_mit_and_attributed(pyproject: dict) -> None:
    """Art. 2: LICENSE at repo root, MIT, (c) 2026 Ernesto Crespo."""
    license_text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in license_text
    assert "2026 Ernesto Crespo" in license_text


def test_readme_carries_attribution_and_non_affiliation() -> None:
    """Art. 2: README must attribute xyflow/React Flow and disclaim affiliation."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "react flow" in readme
    assert "xyflow" in readme
    assert "not affiliated" in readme


def test_runtime_dependencies_are_permissively_licensed(pyproject: dict) -> None:
    """Art. 2: every runtime dep is MIT / Apache-2.0 / BSD-permissive / ISC.

    The mapping is asserted explicitly so that adding a dependency without
    recording its license fails this test rather than slipping through.
    """
    known_licenses = {
        "reflex": "Apache-2.0",
        "networkx": "BSD-3-Clause",
        "langgraph": "MIT",
    }
    declared = list(pyproject["project"]["dependencies"])
    for extra_deps in pyproject["project"].get("optional-dependencies", {}).values():
        declared.extend(extra_deps)

    for requirement in declared:
        name = requirement.split(">")[0].split("<")[0].split("=")[0].split("[")[0].strip()
        assert name in known_licenses, f"undeclared license for runtime dependency {name!r}"
        assert known_licenses[name] in PERMITTED_RUNTIME_LICENSES, (
            f"{name} is {known_licenses[name]}, which Art. 2 does not permit"
        )


# --- Art. 3: naming is settled --------------------------------------------


def test_package_name_and_namespace(pyproject: dict) -> None:
    """Art. 3: only `reflex-react-flow` / `reflex_react_flow`."""
    assert pyproject["project"]["name"] == "reflex-react-flow"
    assert (REPO_ROOT / "custom_components" / "reflex_react_flow" / "__init__.py").is_file()


def test_forbidden_names_absent_from_repo() -> None:
    """Art. 3: `reflex-flow` / `reflex-xyflow` appear nowhere.

    `specs/` and this checker are exempt: the constitution, the PRD, and the
    test that enforces the rule must all be able to *name* the forbidden
    strings in order to forbid them.
    """
    searched = [
        *(REPO_ROOT / "custom_components").rglob("*"),
        *(REPO_ROOT / "tests").rglob("*.py"),
        PYPROJECT,
        REPO_ROOT / "README.md",
    ]
    offenders: list[str] = []
    this_file = Path(__file__).resolve()
    for path in searched:
        if not path.is_file() or path.suffix not in {".py", ".toml", ".md", ".jsx", ".js"}:
            continue
        if path.resolve() == this_file:
            continue
        content = path.read_text(encoding="utf-8").lower()
        for forbidden in FORBIDDEN_NAMES:
            if forbidden in content:
                offenders.append(f"{path.relative_to(REPO_ROOT)}: {forbidden}")
    assert not offenders, f"Art. 3 violation: {offenders}"


# --- package smoke (T-001 Done criterion) ---------------------------------


def test_package_imports_and_exposes_version() -> None:
    """T-001: `import reflex_react_flow` succeeds and carries __version__."""
    import reflex_react_flow

    assert reflex_react_flow.__version__


def test_version_matches_pyproject() -> None:
    """Art. 9: the runtime `__version__` and the published version never drift.

    The release workflow publishes whatever `pyproject.toml` declares, so a stale
    `__version__` would ship a wheel that misreports itself.
    """
    import reflex_react_flow

    declared = tomllib.loads(PYPROJECT.read_text())["project"]["version"]
    assert reflex_react_flow.__version__ == declared
