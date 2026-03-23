#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".bmadx" / "state"
OUT = STATE / "runtime-manifest.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def find_first(*names: str) -> str | None:
    for name in names:
        p = ROOT / name
        if p.exists():
            return name
    return None


def command_in_dir(path: Path, cmd: str) -> str:
    rel = path.relative_to(ROOT)
    if str(rel) == ".":
        return cmd
    return f"cd {rel.as_posix()} && {cmd}"


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def load_toml(path: Path) -> dict:
    if not path.exists() or not tomllib:
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def node_workspace_paths() -> list[Path]:
    candidates: list[Path] = []
    roots = [ROOT, ROOT / "frontend", ROOT / "web", ROOT / "app"]
    for base in roots:
        if (base / "package.json").exists():
            candidates.append(base)
    for parent_name in ("apps", "packages"):
        parent = ROOT / parent_name
        if not parent.exists():
            continue
        for child in sorted(parent.iterdir(), key=lambda p: p.name):
            if child.is_dir() and (child / "package.json").exists():
                candidates.append(child)
    return sorted({path.resolve() for path in candidates}, key=lambda p: str(p))


def node_workspace(path: Path) -> dict:
    pkg = path / "package.json"
    data = read_json(pkg)
    scripts = data.get("scripts", {}) or {}
    if "packageManager" in data:
        pm = str(data["packageManager"]).split("@", 1)[0]
    elif (path / "pnpm-lock.yaml").exists():
        pm = "pnpm"
    elif (path / "yarn.lock").exists():
        pm = "yarn"
    elif (path / "package-lock.json").exists():
        pm = "npm"
    else:
        pm = "npm"

    install_cmd = {
        "pnpm": "pnpm install --frozen-lockfile",
        "yarn": "yarn install --frozen-lockfile",
        "npm": "npm ci" if (path / "package-lock.json").exists() else "npm install",
    }.get(pm, "npm install")

    version_files = []
    for name in (".nvmrc", ".node-version"):
        candidate = path / name
        if candidate.exists():
            version_files.append(str(candidate.relative_to(ROOT)))

    commands = {
        "install": command_in_dir(path, install_cmd),
        "lint": command_in_dir(path, f"{pm} run lint") if "lint" in scripts else "",
        "typecheck": command_in_dir(path, f"{pm} run typecheck") if "typecheck" in scripts else "",
        "test_unit": command_in_dir(path, f"{pm} run test") if "test" in scripts else "",
        "test_integration": command_in_dir(path, f"{pm} run test:integration") if "test:integration" in scripts else "",
        "test_e2e": command_in_dir(path, f"{pm} run test:e2e") if "test:e2e" in scripts else "",
        "build": command_in_dir(path, f"{pm} run build") if "build" in scripts else "",
    }

    return {
        "name": path.name if path != ROOT else "root-node",
        "path": str(path.relative_to(ROOT)),
        "runtime": "node",
        "package_manager": pm,
        "version_files": version_files,
        "commands": commands,
    }


def python_workspace_paths() -> list[Path]:
    candidates: list[Path] = []
    roots = [ROOT, ROOT / "backend", ROOT / "api"]
    for base in roots:
        if (base / "pyproject.toml").exists() or (base / "requirements.txt").exists():
            candidates.append(base)

    services_root = ROOT / "services"
    if services_root.exists():
        for child in sorted(services_root.iterdir(), key=lambda p: p.name):
            if child.is_dir() and ((child / "pyproject.toml").exists() or (child / "requirements.txt").exists()):
                candidates.append(child)

    return sorted({path.resolve() for path in candidates}, key=lambda p: str(p))


def python_workspace(path: Path) -> dict:
    pyproject = path / "pyproject.toml"
    requirements = path / "requirements.txt"
    data = load_toml(pyproject)
    tool = data.get("tool", {}) or {}

    manager = "pip"
    commands = {
        "install": "",
        "lint": "",
        "typecheck": "",
        "test_unit": "",
        "test_integration": "",
        "test_e2e": "",
        "build": "",
    }

    if pyproject.exists() and tomllib:
        if "uv" in tool or (path / "uv.lock").exists():
            manager = "uv"
            commands["install"] = command_in_dir(path, "uv sync")
        elif "poetry" in tool or (path / "poetry.lock").exists():
            manager = "poetry"
            commands["install"] = command_in_dir(path, "poetry install")
        else:
            commands["install"] = command_in_dir(path, "python -m pip install -e .")

        tool_blob = json.dumps(tool).lower()
        if (path / ".ruff.toml").exists() or "ruff" in tool_blob:
            commands["lint"] = command_in_dir(path, "ruff check .")
        if "mypy" in tool_blob:
            commands["typecheck"] = command_in_dir(path, "mypy .")
        if (path / "tests").exists() or "pytest" in tool_blob:
            commands["test_unit"] = command_in_dir(path, "pytest")
        if "build-system" in data:
            commands["build"] = command_in_dir(path, "python -m build")
    elif requirements.exists():
        commands["install"] = command_in_dir(path, "python -m pip install -r requirements.txt")
        if (path / "tests").exists():
            commands["test_unit"] = command_in_dir(path, "pytest")

    version_files = []
    for name in (".python-version",):
        candidate = path / name
        if candidate.exists():
            version_files.append(str(candidate.relative_to(ROOT)))

    migrations = ""
    if (path / "alembic.ini").exists():
        migrations = command_in_dir(path, "alembic upgrade head")
    elif (path / "manage.py").exists():
        migrations = command_in_dir(path, "python manage.py migrate")

    return {
        "name": path.name if path != ROOT else "root-python",
        "path": str(path.relative_to(ROOT)),
        "runtime": "python",
        "package_manager": manager,
        "version_files": version_files,
        "commands": commands,
        "migrations": migrations,
    }


def java_manifest() -> list[dict]:
    if not ((ROOT / "pom.xml").exists() or (ROOT / "build.gradle").exists() or (ROOT / "build.gradle.kts").exists()):
        return []
    gradle = (ROOT / "gradlew").exists() or (ROOT / "build.gradle").exists() or (ROOT / "build.gradle.kts").exists()
    if gradle:
        runner = "./gradlew" if (ROOT / "gradlew").exists() else "gradle"
        return [{
            "name": "root-java",
            "path": ".",
            "runtime": "java",
            "package_manager": "gradle",
            "version_files": [],
            "commands": {
                "install": f"{runner} dependencies || true",
                "lint": "",
                "typecheck": "",
                "test_unit": f"{runner} test",
                "test_integration": "",
                "test_e2e": "",
                "build": f"{runner} build",
            },
        }]
    return [{
        "name": "root-java",
        "path": ".",
        "runtime": "java",
        "package_manager": "maven",
        "version_files": [],
        "commands": {
            "install": "mvn -q -DskipTests dependency:resolve",
            "lint": "",
            "typecheck": "",
            "test_unit": "mvn test",
            "test_integration": "",
            "test_e2e": "",
            "build": "mvn -DskipTests package",
        },
    }]


def go_manifest() -> list[dict]:
    if not (ROOT / "go.mod").exists():
        return []
    return [{
        "name": "root-go",
        "path": ".",
        "runtime": "go",
        "package_manager": "go",
        "version_files": [],
        "commands": {
            "install": "go mod download",
            "lint": "",
            "typecheck": "go test ./...",
            "test_unit": "go test ./...",
            "test_integration": "",
            "test_e2e": "",
            "build": "go build ./...",
        },
    }]


def rust_manifest() -> list[dict]:
    if not (ROOT / "Cargo.toml").exists():
        return []
    version_files = []
    for name in ("rust-toolchain.toml", "rust-toolchain"):
        candidate = ROOT / name
        if candidate.exists():
            version_files.append(name)
    return [{
        "name": "root-rust",
        "path": ".",
        "runtime": "rust",
        "package_manager": "cargo",
        "version_files": version_files,
        "commands": {
            "install": "cargo fetch",
            "lint": "cargo clippy --all-targets --all-features -- -D warnings" if (ROOT / "src").exists() else "",
            "typecheck": "cargo check",
            "test_unit": "cargo test",
            "test_integration": "",
            "test_e2e": "",
            "build": "cargo build",
        },
    }]


def php_manifest() -> list[dict]:
    if not (ROOT / "composer.json").exists():
        return []
    migrations = "php artisan migrate --force" if (ROOT / "artisan").exists() else ""
    return [{
        "name": "root-php",
        "path": ".",
        "runtime": "php",
        "package_manager": "composer",
        "version_files": [],
        "commands": {
            "install": "composer install",
            "lint": "",
            "typecheck": "",
            "test_unit": "vendor/bin/phpunit" if (ROOT / "vendor/bin/phpunit").exists() or (ROOT / "phpunit.xml").exists() else "",
            "test_integration": "",
            "test_e2e": "",
            "build": "",
        },
        "migrations": migrations,
    }]


def aggregate_manifest(workspaces: list[dict]) -> dict:
    commands: dict[str, list[str]] = {
        "install": [],
        "lint": [],
        "typecheck": [],
        "test_unit": [],
        "test_integration": [],
        "test_e2e": [],
        "build": [],
    }
    services: list[str] = []
    migrations: list[str] = []
    version_files: list[str] = []

    for workspace in workspaces:
        version_files.extend(workspace.get("version_files", []))
        for key, value in workspace.get("commands", {}).items():
            if value:
                commands[key].append(value)
        migration = workspace.get("migrations", "")
        if migration:
            migrations.append(migration)

    if (ROOT / "docker-compose.yml").exists() or (ROOT / "compose.yml").exists():
        services.append("docker compose up -d")

    env_files = dedupe([name for name in (find_first(".env.example", ".env.local.example"),) if name])
    detected = dedupe([workspace["runtime"] for workspace in workspaces])
    primary = detected[0] if len(detected) == 1 else ("polyglot" if detected else "unknown")

    return {
        "runtime": {
            "primary": primary,
            "detected": detected,
            "version_files": dedupe(version_files),
        },
        "package_manager": workspaces[0]["package_manager"] if len(workspaces) == 1 else ("multi" if workspaces else "unknown"),
        "workspaces": workspaces,
        "commands": {key: dedupe(values) for key, values in commands.items()},
        "bootstrap": {
            "env_file": env_files[0] if env_files else None,
            "env_files": env_files,
            "services": dedupe(services),
            "migrations": dedupe(migrations),
        },
    }


def merge_overrides(base: dict) -> dict:
    override_path = ROOT / ".bmadx" / "project-contract.json"
    if not override_path.exists():
        return base
    override = read_json(override_path)

    def deep_merge(dst: dict, src: dict) -> dict:
        for key, value in src.items():
            if isinstance(value, dict) and isinstance(dst.get(key), dict):
                dst[key] = deep_merge(dst[key], value)
            else:
                dst[key] = value
        return dst

    return deep_merge(base, override)


def main() -> int:
    STATE.mkdir(parents=True, exist_ok=True)

    workspaces: list[dict] = []
    workspaces.extend(node_workspace(path) for path in node_workspace_paths())
    workspaces.extend(python_workspace(path) for path in python_workspace_paths())
    workspaces.extend(java_manifest())
    workspaces.extend(go_manifest())
    workspaces.extend(rust_manifest())
    workspaces.extend(php_manifest())

    manifest = aggregate_manifest(workspaces)
    manifest = merge_overrides(manifest)
    OUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
