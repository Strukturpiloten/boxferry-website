# Documentation sources

Boxferry.dev assembles documentation from exact Git revisions. This keeps user guidance next to the
code that defines its behavior while publishing one searchable site.

| Content                                                    | Owning repository                                              |
| ---------------------------------------------------------- | -------------------------------------------------------------- |
| BoxFerry CLI, conversion guides, concepts, and diagnostics | [BoxFerry](https://github.com/Strukturpiloten/boxferry)        |
| Compose parsing and native model                           | [ComposeLens](https://github.com/Strukturpiloten/compose-lens) |
| Podman acquisition, discovery, planning, and rendering     | [PodmanLens](https://github.com/Strukturpiloten/podman-lens)   |
| Quadlet parsing, rendering, and compatibility              | [QuadletLens](https://github.com/Strukturpiloten/quadlet-lens) |

Every production build records the repository URL and full commit SHA used for each source. Inspect
the [machine-readable source manifest](https://boxferry.dev/assets/data/documentation-sources.json)
when you need the provenance of the currently published site.

[Browse the documentation](../) · [Get support](../../support/)
