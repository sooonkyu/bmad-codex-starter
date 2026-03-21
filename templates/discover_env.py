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


def node_manifest() -> dict | None:
    pkg = ROOT / "package.json"
    if not pkg.exists():
        return None
    data = read_json(pkg)
    scripts = data.get("scripts", {}) or {}
    if "packageManager" in data:
        pm = str(data["packageManager"]).split("@", 1)[0]
    elif (ROOT / "pnpm-lock.yaml").exists():
        pm = "pnpm"
    elif (ROOT / "yarn.lock").exists():
        pm = "yarn"
    elif (ROOT / "package-lock.json").exists():
        pm = "npm"
    else:
        pm = "npm"
    install_cmd = {
        "pnpm": "pnpm install --frozen-lockfile",
        "yarn": "yarn install --frozen-lockfile",
        "npm": "npm ci" if (ROOT / "package-lock.json").exists() else "npm install",
    }.get(pm, "npm install")
    manifest = {
        "runtime": {"primary": "node", "version_file": find_first(".nvmrc", ".node-version")},
        "package_manager": pm,
        "commands": {
            "install": install_cmd,
            "lint": f"{pm} run lint" if "lint" in scripts else "",
            "typecheck": f"{pm} run typecheck" if "typecheck" in scripts else "",
            "test_unit": f"{pm} run test" if "test" in scripts else "",
            "test_integration": f"{pm} run test:integration" if "test:integration" in scripts else "",
            "test_e2e": f"{pm} run test:e2e" if "test:e2e" in scripts else "",
            "build": f"{pm} run build" if "build" in scripts else "",
        },
        "bootstrap": {
            "env_file": find_first(".env.example", ".env.local.example"),
            "services": ["docker compose up -d"] if ((ROOT / "docker-compose.yml").exists() or (ROOT / "compose.yml").exists()) else [],
            "migrations": "",
        },
    }
    if (ROOT / "prisma").exists():
        manifest["bootstrap"]["migrations"] = f"{pm} exec prisma migrate deploy" if pm != "npm" else "npx prisma migrate deploy"
    return manifest


def python_manifest() -> dict | None:
    pyproject = ROOT / "pyproject.toml"
    req = ROOT / "requirements.txt"
    if not pyproject.exists() and not req.exists():
        return None
    manager = "pip"
    commands = {"install": "", "lint": "", "typecheck": "", "test_unit": "", "test_integration": "", "test_e2e": "", "build": ""}
    if pyproject.exists() and tomllib:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        tool = data.get("tool", {}) or {}
        if "uv" in tool or (ROOT / "uv.lock").exists():
            manager = "uv"; commands["install"] = "uv sync"
        elif "poetry" in tool or (ROOT / "poetry.lock").exists():
            manager = "poetry"; commands["install"] = "poetry install"
        else:
            commands["install"] = "python -m pip install -e ."
        commands["lint"] = "ruff check ." if ((ROOT / ".ruff.toml").exists() or "ruff" in str(tool).lower()) else ""
        commands["typecheck"] = "mypy ." if "mypy" in str(tool).lower() else ""
        commands["test_unit"] = "pytest" if ((ROOT / "tests").exists() or "pytest" in str(tool).lower()) else ""
        commands["build"] = "python -m build" if "build-system" in data else ""
    else:
        commands["install"] = "python -m pip install -r requirements.txt"
        commands["test_unit"] = "pytest" if (ROOT / "tests").exists() else ""
    migrations = ""
    if (ROOT / "alembic.ini").exists():
        migrations = "alembic upgrade head"
    elif (ROOT / "manage.py").exists():
        migrations = "python manage.py migrate"
    return {
        "runtime": {"primary": "python", "version_file": find_first(".python-version")},
        "package_manager": manager,
        "commands": commands,
        "bootstrap": {
            "env_file": find_first(".env.example", ".env.local.example"),
            "services": ["docker compose up -d"] if ((ROOT / "docker-compose.yml").exists() or (ROOT / "compose.yml").exists()) else [],
            "migrations": migrations,
        },
    }


def java_manifest() -> dict | None:
    if not ((ROOT / "pom.xml").exists() or (ROOT / "build.gradle").exists() or (ROOT / "build.gradle.kts").exists()):
        return None
    gradle = (ROOT / "gradlew").exists() or (ROOT / "build.gradle").exists() or (ROOT / "build.gradle.kts").exists()
    if gradle:
        runner = "./gradlew" if (ROOT / "gradlew").exists() else "gradle"
        return {"runtime": {"primary": "java", "version_file": None}, "package_manager": "gradle", "commands": {"install": f"{runner} dependencies || true", "lint": "", "typecheck": "", "test_unit": f"{runner} test", "test_integration": "", "test_e2e": "", "build": f"{runner} build"}, "bootstrap": {"env_file": find_first(".env.example"), "services": [], "migrations": ""}}
    return {"runtime": {"primary": "java", "version_file": None}, "package_manager": "maven", "commands": {"install": "mvn -q -DskipTests dependency:resolve", "lint": "", "typecheck": "", "test_unit": "mvn test", "test_integration": "", "test_e2e": "", "build": "mvn -DskipTests package"}, "bootstrap": {"env_file": find_first(".env.example"), "services": [], "migrations": ""}}


def go_manifest() -> dict | None:
    if not (ROOT / "go.mod").exists():
        return None
    return {"runtime": {"primary": "go", "version_file": None}, "package_manager": "go", "commands": {"install": "go mod download", "lint": "", "typecheck": "go test ./...", "test_unit": "go test ./...", "test_integration": "", "test_e2e": "", "build": "go build ./..."}, "bootstrap": {"env_file": find_first(".env.example"), "services": [], "migrations": ""}}


def rust_manifest() -> dict | None:
    if not (ROOT / "Cargo.toml").exists():
        return None
    return {"runtime": {"primary": "rust", "version_file": find_first("rust-toolchain.toml", "rust-toolchain")}, "package_manager": "cargo", "commands": {"install": "cargo fetch", "lint": "cargo clippy --all-targets --all-features -- -D warnings" if (ROOT / "src").exists() else "", "typecheck": "cargo check", "test_unit": "cargo test", "test_integration": "", "test_e2e": "", "build": "cargo build"}, "bootstrap": {"env_file": find_first(".env.example"), "services": [], "migrations": ""}}


def php_manifest() -> dict | None:
    if not (ROOT / "composer.json").exists():
        return None
    return {"runtime": {"primary": "php", "version_file": None}, "package_manager": "composer", "commands": {"install": "composer install", "lint": "", "typecheck": "", "test_unit": "vendor/bin/phpunit" if (ROOT / "vendor/bin/phpunit").exists() or (ROOT / "phpunit.xml").exists() else "", "test_integration": "", "test_e2e": "", "build": ""}, "bootstrap": {"env_file": find_first(".env.example"), "services": [], "migrations": "php artisan migrate --force" if (ROOT / "artisan").exists() else ""}}


def merge_overrides(base: dict) -> dict:
    override_path = ROOT / ".bmadx" / "project-contract.json"
    if not override_path.exists():
        return base
    override = read_json(override_path)
    def deep_merge(dst: dict, src: dict) -> dict:
        for k, v in src.items():
            if isinstance(v, dict) and isinstance(dst.get(k), dict):
                dst[k] = deep_merge(dst[k], v)
            else:
                dst[k] = v
        return dst
    return deep_merge(base, override)


def main() -> int:
    STATE.mkdir(parents=True, exist_ok=True)
    manifest = node_manifest() or python_manifest() or java_manifest() or go_manifest() or rust_manifest() or php_manifest() or {"runtime": {"primary": "unknown", "version_file": None}, "package_manager": "unknown", "commands": {"install": "", "lint": "", "typecheck": "", "test_unit": "", "test_integration": "", "test_e2e": "", "build": ""}, "bootstrap": {"env_file": find_first(".env.example", ".env.local.example"), "services": [], "migrations": ""}}
    manifest = merge_overrides(manifest)
    OUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
