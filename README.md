# Docker images for TLS implementations

This repository contains the scripts to automatically build Docker images of
every version of multiple different TLS implementations. The primary goal of
these Docker images is to facilitate fingerprint extraction for `tlsprint`, but
they can be for a variety of other purposes purposes (analyzing specific
versions, penetration test lab environments, etc.).

Each supported version is stored in its own submodule. The python script
`update_repositories.py` is used to generate a Dockerfile for every version of
every implementation, based on the Dockerfile.j2 template stored in the
submodule.
