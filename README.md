# Docker images for TLS implementations

This repository is part of the `tlsprint` project. It acts an umbrella project
for all implementation specific repositories used to build Docker images. Even
though the primary goal of these Docker images is to facilitate fingerprint
extraction for `tlsprint`, they can also be used for a variety of other
purposes purposes (analyzing specific versions, penetration test lab
environments, etc.). The resulting Docker images can be found on [Docker
Hub](https://hub.docker.com/u/tlsprint).

Each supported TLS implementation is stored in its own submodule, but they all
have an identical directory structure. They all contain:

-   `upstream`: This is a submodule referencing the upstream repository, the
    source code of the actual implementation. For example, for OpenSSL this
    points to <https://github.com/openssl/openssl.git> and for mbed TLS it points
    to <https://github.com/ARMmbed/mbedtls.git>.
-   `dockerfiles`: In this directory, each version of this implementation has
    a directory containing a `Dockerfile`. This `Dockerfile` can be used to
    build the Docker image for that specific version. Each file is self
    contained, which allows the inspection of the specific build steps, and
    allows building a single specific version.
-   `Dockerfile.j2`: From this template, all dockerfiles are generated. The
    template takes some values (such as upstream URL, tag, etc.), and contains
    the logic which results in the eventual `Dockerfile`. This logic largely
    includes running certain commands, or setting different values, based on
    the target version. By placing all the logic in this single template file,
    it creates a single source of truth about how the implementation should be
    compiled for different versions.
-   `__init__.py`: This file turns the directory into a Python package with two
    handler functions: `extract_versions(tags)` and
    `get_supported_tls(version)`. These handler functions are called by the
    update scripts of `tlsprint/tls-docker-images` and `tlsprint/models`.
-   `.drone.yml`: This file defines the configuration for Drone CI, it is
    generated using the `.drone.yml.j2` template file from
    `tlsprint/tls-docker-images`. Because each repository contains
    a `.drone.yml` file, they can all be added to Drone CI and run
    independently. The Drone pipeline currently performs the following actions
    for every supported version of the implementation:
    -   Build the Docker image.
    -   Verify that a TLS handshake can be performed (for all TLS versions
        supported by this implementation version).
    -   Publish the Docker image to DockerHub.

When configuring a new implementation to be added to this repository and to
`tlsprint`, this file structure is important. It is however tedious to create
it from scratch every time, so there is also a template repository called
[`tlsprint/tlsprint/implementation-template`][template-url]. This templates
leverages [Cookiecutter][cookiecutter], a project template framework, for ease
use of use. After installing Cookiecutter, a new implementation specific
repository can be added by running `cookiecutter
https://github.com/tlsprint/implementation-template` and filling in the
prompted values. This will create the necessary files with some stub content,
initialize a Git repository, add the upstream repository as a submodule and
create an initial commit of it all. An example run is shown below:

[template-url]: https://github.com/tlsprint/implementation-template
[cookiecutter]: https://cookiecutter.readthedocs.io/

```bash
~> cookiecutter https://github.com/tlsprint/implementation-template
implementation_name [some-tls]: OpenSSL
implementation_slug [openssl]:
upstream_url [https://github.com/openssl/openssl.git]:
Initialized empty Git repository in /home/erwin/workspace/temp/docker-openssl/.git/
Cloning into '/home/erwin/workspace/temp/docker-openssl/upstream'...
remote: Enumerating objects: 3, done.
remote: Counting objects: 100% (3/3), done.
remote: Compressing objects: 100% (3/3), done.
remote: Total 337806 (delta 0), reused 1 (delta 0), pack-reused 337803
Receiving objects: 100% (337806/337806), 169.90 MiB | 17.24 MiB/s, done.
Resolving deltas: 100% (231462/231462), done.
[master (root-commit) 7d5693d] Initialize repository for OpenSSL
 4 files changed, 58 insertions(+)
 create mode 100644 .gitmodules
 create mode 100644 Dockerfile.j2
 create mode 100644 __init__.py
 create mode 160000 upstream
```

To update all implementation submodules (fetch new versions, refresh from
template), the Python script `update_repositories.py` is used. This script
performs the following actions for every implementation submodule:

-   Fetch new tags and extract version information.
-   From the `Dockerfile.j2`, generate a `Dockerfile` for each version.
-   Generate `.drone.yml` from the `.drone.yml.j2` template.
-   Commit changed files and upstream reference.
