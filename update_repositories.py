import os
from pathlib import Path
from importlib import import_module
from distutils.version import LooseVersion

import pygit2
from jinja2 import Template

# Every implementation is stored in a separate directory, looping over them
# allows updated each of them.
implementations = [
    ("botan", "https://github.com/randombit/botan.git"),
    ("mbedtls", "https://github.com/ARMmbed/mbedtls.git"),
    ("openssl", "https://github.com/openssl/openssl.git"),
]

for (implementation, url) in implementations:
    path = Path(implementation)
    repo = pygit2.Repository(pygit2.discover_repository(implementation))

    upstream_directory = str(path / "upstream")
    upstream = pygit2.Repository(pygit2.discover_repository(upstream_directory))

    # TODO: Update the upstream repository and fetch the latest tags

    # Get a list of all Git tags in the upstream
    tags = [ref for ref in upstream.references if ref.startswith("refs/tags/")]

    # Remove the 'refs/tags/' prefix from the tag names
    tags = [tag.replace("refs/tags/", "") for tag in tags]

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
    with open(path / "Dockerfile.j2") as f:
        template = Template(f.read())

    for info in version_info:
        # Create the folder for this tag
        tag_dir = path / "dockerfiles" / info["version"]
        tag_dir.mkdir(parents=True, exist_ok=True)

        # Write the created Dockerfile to the folder
        with open(tag_dir / "Dockerfile", "w") as f:
            f.write(template.render(implementation=implementation, url=url, tag=info["tag"], version=info["version"]))

    # Generate a .drone.yml that builds each Dockerfile
    with open(".drone.yml.j2") as f:
        drone_template = Template(f.read())

    with open(path / ".drone.yml", "w") as f:
        f.write(drone_template.render(implementation=implementation, version_info=version_info, settings=settings))
