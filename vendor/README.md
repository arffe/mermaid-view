# vendor/

`mermaid.min.js` is [Mermaid](https://github.com/mermaid-js/mermaid),
unmodified, kept here so the viewer works offline and never changes behind
your back.

| | |
|---|---|
| Version | 11.12.0 |
| Source | https://cdn.jsdelivr.net/npm/mermaid@11.12.0/dist/mermaid.min.js |
| SHA-256 | `07e37dfa97b337ccc85365d57eddf99b9706f09db3b59b260d0333b23b343c4b` |
| Licence | MIT (see `../THIRD_PARTY_NOTICES.md`) |

To update, run `tools/update-mermaid <version>`. It downloads the new file,
checks that it is the browser (UMD) build, and rewrites the table above.
Then open a few diagrams, especially one with a subgraph and an XY chart:
`viewer.html` works around two Mermaid quirks there that a new version
could change.
