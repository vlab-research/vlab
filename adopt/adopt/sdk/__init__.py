"""The vlab SDK: author a study from a file, without the dashboard.

Phase 3 of `planning/agent-study-authoring.md` §8, and the piece §14.6 says the
whole-study validator was built for. `planning/vlab-sdk.md` records what
shipped and why.

Three modules, and the split is deliberate:

* `client` — HTTP only. Auth header, base URL, one typed exception per status
  the service actually returns. It knows nothing about study files.
* `study` — the file on disk. Load, save, diff against what is stored, and the
  order sections have to be written in. Pure; it never opens a socket.
* `cli` — `click`. Argument parsing and printing, and nothing else that a
  library caller would want.

That layering is what makes the SDK usable as a library. A notebook that wants
`adopt.authoring.strata.create_strata_from_variables` to build strata out of a
spreadsheet and then push them can use `StudyFile` and `VlabClient` directly
without going through argv, which is the composability §6.D of the plan
insists on: the authoring library is primitives, and the CLI is one caller of
them rather than the only way in.

Installed as an extra, from the repository -- `adopt` is on no package index,
and the name `adopt` on PyPI is an unrelated project::

    pipx install --python python3.10 \\
      "adopt[sdk] @ git+https://github.com/vlab-research/vlab.git#subdirectory=adopt"

Python >=3.9,<3.11, which is `adopt`'s own constraint. The extra exists for the
console script and `click`; everything else the SDK needs (`requests`,
`PyYAML`, pydantic, the authoring library) is already a hard dependency of
`adopt` -- which is also why the install is not small. `adopt/README.md` has
the in-checkout `poetry install --extras sdk` path and the verification.
"""

from .client import (
    DEFAULT_API_URL,
    ConflictError,
    ForbiddenError,
    NotAuthenticatedError,
    NotFoundError,
    ServerError,
    TransportError,
    UnprocessableError,
    VlabClient,
    VlabError,
    VlabHTTPError,
)
from .study import (
    PUSH_ORDER,
    SECTION_URL_SEGMENTS,
    SectionDiff,
    StudyFile,
    diff_sections,
    skeleton,
    unknown_keys,
)

__all__ = [
    "DEFAULT_API_URL",
    "PUSH_ORDER",
    "SECTION_URL_SEGMENTS",
    "ConflictError",
    "ForbiddenError",
    "NotAuthenticatedError",
    "NotFoundError",
    "SectionDiff",
    "ServerError",
    "StudyFile",
    "TransportError",
    "UnprocessableError",
    "VlabClient",
    "VlabError",
    "VlabHTTPError",
    "diff_sections",
    "skeleton",
    "unknown_keys",
]
