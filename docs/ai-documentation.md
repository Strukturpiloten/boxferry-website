# AI-readable documentation

The website builds `/llms.txt`, `/docs/llms.txt`, and stable Markdown alternatives for authored
documentation pages from the same staged Markdown as the human-readable site. The HTML head of
each such page links to its Markdown alternative and describes it with `/docs/llms.txt`.
`/llms-full.txt` is published only while the assembled authored corpus remains within 2 MiB; the
indexes remain available if it grows beyond that bound. The index is limited to 256 KiB.

The build takes source repository URLs and exact revisions from `documentation-sources.toml`.
Alternatives preserve the authored Markdown without copying it into this repository. Generated
Rustdoc HTML is not converted to Markdown, and diagnostic rule pages derived from the checked
catalogue are not treated as authored pages. The publisher runs after the strict site build;
`verify_site.py` checks the routes against the staged sources, catching missing, stale, and extra
alternatives. Public indexes contain source URLs and revisions, not checkout locations or runtime
credentials. The generated files under `.generated/` and `site/` remain uncommitted.

For a unified site view, an AI documentation consumer can use
`https://boxferry.dev/docs/llms.txt` (or the smaller root index at `https://boxferry.dev/llms.txt`).
The [neuledge/context CLI](https://github.com/neuledge/context#beyond-registry) documents
`context add https://your-site`, which discovers `llms-full.txt` or `llms.txt`, and direct URLs such
as `context add https://boxferry.dev/docs/llms.txt`. It also documents repository-local use with
`context add https://github.com/Strukturpiloten/boxferry --path docs`; substitute `compose-lens`,
`podman-lens`, or `quadlet-lens` for an individual Lens repository. A local checkout can be added
with `context add ./repo --path docs`. These are consumer examples, not automated submissions.

Context7 registration is a separate maintainer action. Its [Add a Library
page](https://context7.com/add-library) accepts public GitHub repository URLs on the GitHub tab.
The four source repositories to add individually are
`Strukturpiloten/boxferry`, `Strukturpiloten/compose-lens`, `Strukturpiloten/podman-lens`, and
`Strukturpiloten/quadlet-lens`; their technical documentation remains at source. An optional
repository-root `context7.json` can refine parsing if the owner wants that. A repository owner may
then follow Context7's [claiming guide](https://context7.com/howto/claiming-libraries). This
repository does not submit or claim a listing on the maintainer's behalf.
