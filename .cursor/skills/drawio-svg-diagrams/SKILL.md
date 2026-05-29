---
name: drawio-svg-diagrams
description: Standard format, validation workflow, and authoring guidance for draw.io .drawio.svg diagrams. Includes visible connector defaults and sequence-diagram lifeline patterns. Use when creating, editing, validating, or troubleshooting .drawio.svg files or drawio_svg.py.
---

# Draw.io SVG Format

This skill covers the `.drawio.svg` shell, encode/decode, and CLI workflow. **Authoring the inner mxGraph XML** (styles, edges, containers, layers, tags, dark mode, well-formedness) follows the vendored **[`xml-reference.md`](xml-reference.md)** — adapted from [jgraph/drawio-mcp `shared/xml-reference.md`](https://github.com/jgraph/drawio-mcp/blob/main/shared/xml-reference.md) (Apache-2.0). Read that file when generating or editing diagram XML; `drawio_svg.py` enforces a subset of its rules during validation.

**Also follow this skill’s sections below** — especially **Visible connectors** and **UML sequence diagrams** — so diagrams stay readable in Git previews and exports without relying on any project-local generator script.

This repository stores draw.io diagrams as `.drawio.svg` with a compressed diagram payload inside the `<svg>` element's `content` attribute.

## Content Attribute Format

The `content` attribute MUST contain an HTML-entity-encoded `mxfile` wrapper with a compressed `<diagram>` payload:

```text
&lt;mxfile&gt;&lt;diagram id=&quot;d&quot; name=&quot;P&quot;&gt;BASE64(deflateRaw(encodeURIComponent(mxGraph XML)))&lt;/diagram&gt;&lt;/mxfile&gt;
```

Encode/decode logic (matches `drawio-mcp`):

- Encode: `deflateRaw(encodeURIComponent(xml)) -> base64`
- Decode: `base64 -> inflateRaw -> decodeURIComponent`

## Outer SVG Requirements

- Minimal but complete `<svg>` shell: `xmlns`, `xmlns:xlink`, `version`, `width`, `height`, `viewBox`
- `style="background-color: rgb(255, 255, 255);"`
- `content` attribute with HTML-entity-encoded compressed mxGraph model
- Minimal body with `<defs/>` and `<g>` containing a white background rectangle
- The draw.io editor regenerates the visual SVG layer from the mxGraph model

Shell template:

```xml
<svg host="65bd71144e" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" width="1200px" height="900px" viewBox="-0.5 -0.5 1200 900" content="..." style="background-color: rgb(255, 255, 255);">
  <defs/>
  <g>
    <rect x="-0.5" y="-0.5" width="1200" height="900" fill="#FFFFFF" stroke="none"/>
  </g>
</svg>
```

## drawio_svg.py Commands

| Command | Usage |
| --- | --- |
| `init-empty --file <svg>` | Create new empty `.drawio.svg` with minimal mxGraphModel |
| `rebuild --file <svg> --xml <mx.xml>` | Delete existing SVG and rebuild from mxGraph XML |
| `extract --file <svg>` | Extract and print decoded mxGraph XML |
| `validate --file <svg>` | Validate SVG shell, graph structure, and **xml-reference.md rules** |
| `validate --file <svg> --shell-only` | Validate SVG shell structure only |
| `validate --file <svg> --no-ref-checks` | Skip reference-only rules (comments, duplicate ids, edge `mxGeometry`) |
| `validate-xml --file <xml>` | Validate mxGraph XML (same rules as full `validate`) |
| `validate-xml --file <xml> --no-ref-checks` | Structural checks only (plus edge/parent warnings), no reference hard-fails |
| `--test` | Run the built-in test suite |

Optional flags for `init-empty` and `rebuild`: `--diagram-id`, `--diagram-name`, `--width`, `--height`, `--viewBox`.

## Recommended Workflow (Editing Existing Diagrams)

The `.drawio.svg` file is always the source of truth.

1. **Extract** current diagram XML into a sidecar file:

   ```bash
   python3 .cursor/skills/drawio-svg-diagrams/drawio_svg.py extract --file svg/diagram.drawio.svg > svg/diagram.model.xml
   ```

2. **Edit** `svg/diagram.model.xml` (add/remove cells, ensure `background="#FFFFFF"`, adjust styles). Follow **[`xml-reference.md`](xml-reference.md)** for shapes, edge routing (`<mxGeometry relative="1">` on every edge), containers, escaping, and the ban on XML comments. **Set explicit `strokeColor` (and arrows) on every edge** per **Visible connectors** below so lines are not washed out in `.drawio.svg`.

3. **Rebuild** the SVG (deletes old file, creates fresh one, auto-generates new diagram ID/name):

   ```bash
   python3 .cursor/skills/drawio-svg-diagrams/drawio_svg.py rebuild --file svg/diagram.drawio.svg --xml svg/diagram.model.xml
   ```

4. **Validate** the result:

   ```bash
   python3 .cursor/skills/drawio-svg-diagrams/drawio_svg.py validate --file svg/diagram.drawio.svg
   ```

Sidecar `*.model.xml` files in the same folder as the SVG are **auto-deleted** after a successful rebuild.

## Alternative Workflows

- **New diagram**: Create a `model.xml` with `<mxGraphModel ... background="#FFFFFF">`, then `rebuild --file new.drawio.svg --xml model.xml`
- **Empty diagram**: `init-empty --file path/to/empty.drawio.svg`
- **Validate XML before rebuild**: `validate-xml --file svg/diagram.model.xml`
- **Background color**: `mxGraphModel` must include `background="#FFFFFF"` -- add it in the extracted XML if missing

## Validation Details

**Full validation** (`validate --file <svg>`) checks:

- SVG shell structure (`<svg>`, `<defs>`, `<g>`)
- `content` attribute presence and format
- Successful base64 decode -> inflateRaw -> URI decode
- Parses `<mxGraphModel>` / `<root>` (including all descendant `mxCell` nodes, e.g. under `<object>`)
- Required root cells `mxCell id="0"` and `mxCell id="1"`
- **From [`xml-reference.md`](xml-reference.md)** (unless `--no-ref-checks`):
  - No XML comments (`<!--`) anywhere in the diagram XML string
  - Unique `id` across `<mxCell>` and `<object>` elements
  - Every `edge="1"` cell has a child `<mxGeometry relative="1" as="geometry"/>`
- Warns if any `vertex="1"` cell lacks `<mxGeometry>` (see reference examples)
- Warns if `background` on `<mxGraphModel>` is not `#FFFFFF`
- Warns if edges lack `source`/`target` or reference unknown ids
- Warns if a cell’s `parent` is not a known id
- **When `--no-ref-checks` is not used:** warns if any edge’s `style` omits `strokeColor=` (invisible connectors in static SVG), and if an edge has a **non-empty** `value` label but omits `labelBackgroundColor=` (opaque label box in `.drawio.svg`); fix using **Visible connectors** below

**XML validation** (`validate-xml --file <xml>`) runs the same graph and reference checks on a standalone file (`<mxfile>`, `<diagram>`, or `<mxGraphModel>`).

## Encode/Decode Snippets (Python stdlib)

```python
from urllib.parse import quote, unquote
import zlib, base64

def encode(xml: str) -> str:
    pct = quote(xml)
    comp = zlib.compressobj(level=9, wbits=-15)
    data = comp.compress(pct.encode('utf-8')) + comp.flush()
    return base64.b64encode(data).decode('ascii')

def decode(b64: str) -> str:
    data = base64.b64decode(b64)
    xml_pct = zlib.decompress(data, wbits=-15).decode('utf-8')
    return unquote(xml_pct)
```

## Visible connectors (mandatory for readable `.drawio.svg`)

Default draw.io edge styling often relies on the editor theme. **Compressed `.drawio.svg` in git is viewed without that theme**, so connectors can look missing or extremely low contrast. **Always set edge stroke and arrow explicitly** on every `edge="1"` cell.

**Edge label background:** In static SVG / some viewers, edge labels otherwise get an **opaque dark box** behind the text. Add **`labelBackgroundColor=none`** to every edge that has a `value` label (or to all edges for consistency).

**Solid directed edge (most flows, associations, transitions):**

```text
edgeStyle=orthogonalEdgeStyle;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#000000;strokeWidth=2;fontColor=#222222;labelBackgroundColor=none;endArrow=classic;endFill=1;startArrow=none;rounded=0;
```

**Dashed (return messages, optional flows, realization-style emphasis):**

```text
edgeStyle=orthogonalEdgeStyle;orthogonalLoop=1;jettySize=auto;html=1;dashed=1;dashPattern=8 8;strokeColor=#000000;strokeWidth=2;fontColor=#222222;labelBackgroundColor=none;endArrow=classic;endFill=1;startArrow=none;rounded=0;
```

**Open arrow (dependency / package “uses”):**

```text
edgeStyle=orthogonalEdgeStyle;html=1;dashed=1;strokeColor=#000000;strokeWidth=2;fontColor=#222222;labelBackgroundColor=none;endArrow=open;startArrow=none;rounded=0;
```

**Interface realization (hollow triangle):**

```text
edgeStyle=orthogonalEdgeStyle;html=1;dashed=1;strokeColor=#000000;strokeWidth=2;fontColor=#222222;labelBackgroundColor=none;endArrow=block;endFill=0;startArrow=none;rounded=0;
```

**Node outlines** on white canvas: prefer `strokeColor=#000000` and `strokeWidth=2` on swimlanes, classes, components, use-case ovals, and system-boundary rectangles so shapes do not disappear next to black edges.

**Shape fills:** Always set an explicit **`fillColor`** on vertices (especially **`shape=cylinder3`** and other stencils). In `.drawio.svg` static preview, omitting `fillColor` can render as **solid black** even though the desktop editor shows a theme default. Use a light fill (e.g. `fillColor=#dae8fc`) plus `strokeColor=#000000` — **do not** use `fillColor=#000000` for body fills unless you intentionally want a black box (then use `fontColor=#FFFFFF`).

**UML sequence diagrams** must not route all messages only between the header boxes at the top (unreadable). See the next section.

## UML sequence diagrams

Model the timeline explicitly:

1. **Header** `mxCell` per participant (`vertex="1"`, rounded rectangle or cylinder for DB) at the top.
2. **Lifeline** per participant: a **thin vertical** `vertex="1"` under the header, e.g. `x` aligned to header center, `width="4"`, `height` spanning the diagram, style like `fillColor=none;strokeColor=#000000;strokeWidth=2;dashed=1;dashPattern=6 6;`.
3. **Optional** thin dashed `edge="1"` from each header’s bottom to the top of its lifeline (`endArrow=none`, `strokeWidth=1`, `labelBackgroundColor=none`) so the eye links name to line.
4. **Messages** are `edge="1"` cells whose **`source` and `target` are lifeline ids**, not header ids. Give each message a **different vertical position** using port constraints on the edge style, e.g. `exitX=0.5;exitY=0.12;entryX=0.5;entryY=0.12;` where `exitY`/`entryY` are **0–1 fractions along the lifeline geometry** (`exitY = (messageY - lifelineTop) / lifelineHeight`). Increment `messageY` down the page for successive calls; use the dashed edge style for replies.

This matches how readable sequence diagrams are authored in draw.io and survives `extract` → edit → `rebuild` without a separate generator.

## Label Colors

- **Default**: `fontColor=#222222` (dark neutral, readable on white backgrounds)
- **Light backgrounds** (`#FFFFFF`, `#FFF3E0`, `#E3F2FD`, etc.): use `fontColor=#222222`
- **Dark backgrounds** (`#4CAF50`, `#6A1B9A`, `#1976D2`): use `fontColor=#FFFFFF`
- **Edge labels**: always set `labelBackgroundColor=none` on the edge `style` so labels stay readable in `.drawio.svg` (otherwise the label often renders with an opaque dark background)

## Layout and Padding

- Keep content visually inset from container borders
- For legend-style swimlanes: inner left/right margin ~12px (`x="12"`, width reduced by ~24px)
- First child row below header: for `startSize=24`, use `y~32`, stack with ~8px vertical gap

## UML Diagrams (general)

- Use consistent fill and **black stroke** (`strokeColor=#000000`) across diagram types so exports match the editor.
- Prefer horizontal alignment for participants/lanes, clear vertical spacing for steps (see `xml-reference.md` spacing guidance).
- **Sequence**: follow **UML sequence diagrams** above — lifelines + `exitY`/`entryY`, not header-to-header edges only.

## Authoring Guidance

- Treat `.drawio.svg` as the canonical source of truth
- Always start by extracting latest XML, then rebuild -- never reuse stale `*.model.xml`
- Always use `rebuild` (not manual edits to SVG) to prevent caching issues
- Run `python3 .cursor/skills/drawio-svg-diagrams/drawio_svg.py --test` before modifying the script
