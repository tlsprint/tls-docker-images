import datetime
import logging
from distutils.version import LooseVersion
from importlib import import_module
from pathlib import Path

import click
from jinja2 import Environment

import git

logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)


def in_version_range(version, left, right):
    """Jinja2 filter to see if a version falls without a certain range."""
    if left is None:
        return LooseVersion(version) <= LooseVersion(right)
    elif right is None:
        return LooseVersion(left) <= LooseVersion(version)
    else:
        return LooseVersion(left) <= LooseVersion(version) <= LooseVersion(right)


def update_implementation(implementation, url, env, *, commit=False):
    repo_path = Path(implementation)
    repo = git.Repo(repo_path)

    # If the `commit` option is not passed, it is probably in development mode.
    # Pulling at such a moment is not a good idea, as there will be local
    # changes.
    if commit:
        logger.info(f"{implementation}: Pull most recent version")
        repo.git.checkout("master")
        repo.git.pull("--rebase")

    logger.info(f"{implementation}: Update upstream submodule")
    upstream = repo.submodules.upstream.module()
    upstream.git.checkout("master")
    upstream.git.pull("--rebase")

    # Get a list of all Git tags in the upstream
    logger.info(f"{implementation}: Get tag information from upstream")
    tags = [tag.name for tag in upstream.tags]

    # Filter the rest of the tags with implementation dependent rules, and
    # extract the actual version numbers from the tags.
    module = import_module(implementation)
    version_info = module.extract_versions(tags)
    version_info = sorted(version_info, key=lambda info: LooseVersion(info["version"]))

    try:
        settings = module.settings
    except AttributeError:
        settings = dict()

    # Read the Dockerfile template
    logger.info(f"{implementation}: Generating dockerfiles")
    with open(repo_path / "Dockerfile.j2") as f:
        template = env.from_string(f.read())

    for info in version_info:
        # Create the folder for this tag
        tag_dir = repo_path / "dockerfiles" / info["version"]
        tag_dir.mkdir(parents=True, exist_ok=True)

        # Write the created Dockerfile to the folder
        with open(tag_dir / "Dockerfile", "w") as f:
            f.write(
                template.render(
                    implementation=implementation,
                    url=url,
                    tag=info["tag"],
                    version=info["version"],
                )
            )

    # Generate a .drone.yml that builds each Dockerfile
    logger.info(f"{implementation}: Generating .drone.yml")
    with open(".drone.yml.j2") as f:
        drone_template = env.from_string(f.read())

    with open(repo_path / ".drone.yml", "w") as f:
        f.write(
            drone_template.render(
                implementation=implementation,
                version_info=version_info,
                settings=settings,
            )
        )

    if commit:
        logger.info(f"{implementation}: Attempt to commit changes")
        try:
            repo.git.add(".")
            repo.git.commit(message=f"Automatic update {datetime.date.today()}")
            repo.git.push()
            logger.info(f"{implementation}: Committed changes")
        except git.exc.GitCommandError:
            logger.info(f"{implementation}: No changes committed")


@click.command()
@click.option(
    "--commit",
    default=False,
    is_flag=True,
    help="Flag to indicate if changes should be committed",
)
def main(commit):
    # Configure the Jinja2 environment, including the custom filter
    env = Environment()
    env.filters["in_version_range"] = in_version_range

    # Every implementation is stored in a separate directory, looping over them
    # allows updating each of them.
    implementations = [
        ("botan", "https://github.com/randombit/botan.git"),
        ("mbedtls", "https://github.com/ARMmbed/mbedtls.git"),
        ("openssl", "https://github.com/openssl/openssl.git"),
    ]

    # Initialize a repository to commit the updated submodules
    if commit:
        repo = git.Repo(".")
        # Since this script is supposed to run autonomously on the master
        # branch, we make the (potentially dangerous) assumption that we need
        # to checkout the master branch (since the CI is in detached state).
        repo.git.checkout("master")
        repo.git.pull("--rebase")

    for (implementation, url) in implementations:
        update_implementation(implementation, url, env, commit=commit)

        if commit:
            repo.git.add(implementation)

    # Commit the changed submodules
    if commit:
        try:
            repo.git.commit(message=f"Automatic update {datetime.date.today()}")
            repo.git.push()
            logger.info(f"Updated submodule references")
        except git.exc.GitCommandError:
            logger.info(f"No submodule references updated")


if __name__ == "__main__":
    main()
