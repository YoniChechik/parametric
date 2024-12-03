import subprocess
import sys
from datetime import datetime
from enum import Enum

import tomlkit


class ReleaseType(str, Enum):
    PATCH = "patch"
    MINOR = "minor"
    MAJOR = "major"

    @staticmethod
    def list():
        return list(map(lambda rt: rt.value, ReleaseType))


def _bump_version(version, release_type):
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


def update_pyproject_version(release_type):
    with open("pyproject.toml") as f:
        pyproject = tomlkit.parse(f.read())

    # Ensure 'project' and 'dependencies' sections exist
    if "project" not in pyproject:
        pyproject["project"] = tomlkit.table()

    # Bump version
    current_version = pyproject["project"]["version"]
    new_version = _bump_version(current_version, release_type)

    pyproject["project"]["version"] = new_version

    with open("pyproject.toml", "w") as f:
        f.write(tomlkit.dumps(pyproject))

    return current_version, new_version


def _get_commits_since_last_version(last_version):
    result = subprocess.run(
        ["git", "log", f"v{last_version}..HEAD", "--pretty=format:%s"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get commit logs: {result.stderr}")
    return result.stdout.splitlines()


def update_changelog(last_version, new_version):
    commits = _get_commits_since_last_version(last_version)

    date_str = datetime.now().strftime("%Y-%m-%d")
    changelog_entry = f"## [{new_version}] - {date_str}\n\n"

    for commit in commits:
        changelog_entry += f"- {commit}\n"

    changelog_entry += "\n"

    # Prepend to CHANGELOG.md
    with open("CHANGELOG.md", "r+") as changelog_file:
        existing_content = changelog_file.read()
        changelog_file.seek(0, 0)
        changelog_file.write(changelog_entry + existing_content)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ReleaseType.list():
        raise ValueError(
            f"Usage: update_pyproject.py <release_type>; Available release types: {', '.join(ReleaseType.list())}",
        )

    release_type = sys.argv[1]
    last_version, new_version = update_pyproject_version(release_type)

    # Update CHANGELOG.md
    update_changelog(last_version, new_version)

    # used as the output of this script to get the version
    print(new_version)
