import sys
from enum import Enum

import tomlkit


class ReleaseType(str, Enum):
    PATCH = "patch"
    MINOR = "minor"
    MAJOR = "major"

    @staticmethod
    def list():
        return list(map(lambda rt: rt.value, ReleaseType))


def parse_requirements(filename):
    with open(filename, "r") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def bump_version(version, release_type):
    major, minor, patch = map(int, version.split("."))
    if release_type == ReleaseType.PATCH:
        patch += 1
    elif release_type == ReleaseType.MINOR:
        minor += 1
        patch = 0
    elif release_type == ReleaseType.MAJOR:
        major += 1
        minor = 0
        patch = 0
    else:
        raise ValueError(f"Invalid release type: {release_type}")
    return f"{major}.{minor}.{patch}"


def update_pyproject(dependencies, release_type):
    with open("pyproject.toml", "r") as f:
        pyproject = tomlkit.parse(f.read())

    # Ensure 'project' and 'dependencies' sections exist
    if "project" not in pyproject:
        pyproject["project"] = tomlkit.table()
    if "dependencies" not in pyproject["project"]:
        pyproject["project"]["dependencies"] = tomlkit.array()

    # Update dependencies
    pyproject["project"]["dependencies"].clear()
    for dep in dependencies:
        pyproject["project"]["dependencies"].append(dep)

    # Bump version
    current_version = pyproject["project"]["version"]
    new_version = bump_version(current_version, release_type)

    pyproject["project"]["version"] = new_version

    with open("pyproject.toml", "w") as f:
        f.write(tomlkit.dumps(pyproject))

    return new_version


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ReleaseType.list():
        raise (f"Usage: update_pyproject.py <release_type>; Available release types: {', '.join(ReleaseType.list())}")

    release_type = sys.argv[1]
    deps = parse_requirements("requirements_prod.txt")
    new_version = update_pyproject(deps, release_type)
    # used as the output of this script to get the version
    print(f"{new_version}")
