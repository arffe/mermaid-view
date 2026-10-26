# Third-party notices

This project's own code is under the MIT licence (see `LICENSE`). It also
ships one third-party file, and uses some system libraries it does not ship.

## Shipped: `vendor/mermaid.min.js`

[Mermaid](https://github.com/mermaid-js/mermaid) 11.12.0, unmodified, as
published on npm (`dist/mermaid.min.js`). Its licence:

```
The MIT License (MIT)

Copyright (c) 2014 - 2022 Knut Sveidqvist

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

The file bundles these libraries, whose licence notices are kept in the
"Bundled license information" comment at the end of the file:

| Library | Version | Licence |
|---|---|---|
| [DOMPurify](https://github.com/cure53/DOMPurify) | 3.2.6 | Apache-2.0 or MPL-2.0 (dual) |
| [js-yaml](https://github.com/nodeca/js-yaml) | 4.1.0 | MIT |
| [lodash-es](https://lodash.com/) | (bundled) | MIT |
| [Cytoscape.js](https://github.com/cytoscape/cytoscape.js) | (bundled) | MIT, including parts derived from jQuery and Framer.js (MIT) |

Mermaid also bundles other MIT/ISC-licensed packages (such as d3 and dagre)
whose notices are not repeated in the minified file; see Mermaid's
`package.json` for the full dependency list.

## Used but not shipped

Installed by the user's package manager and loaded at run time:

| Component | Licence |
|---|---|
| GTK 4, WebKitGTK 6.0, PyGObject | LGPL-2.1-or-later |
| wl-clipboard | GPL-3.0 |
| Python 3 | PSF License |

`wl-clipboard` is only run as a separate program (`wl-paste`), not linked.
