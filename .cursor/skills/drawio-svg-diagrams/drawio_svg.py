#!/usr/bin/env python3
"""
drawio_svg.py

Minimal utility for managing .drawio.svg files that store compressed mxGraph models
in the `content` attribute. The draw.io editor regenerates the visual layer.

Key invariants:
  - Minimal SVG shell: <svg><defs/><g/></svg> (no inline drawings)
  - content="&lt;mxfile&gt;&lt;diagram ...&gt;BASE64(deflateRaw(encodeURIComponent(mxGraph XML)))&lt;/diagram&gt;&lt;/mxfile&gt;"
  - Auto-generates fresh diagram ids/names to avoid Cursor cache issues

Subcommands:
  - init-empty --file <svg> [--diagram-id <id>] [--diagram-name <name>] [--width <w>] [--height <h>] [--viewBox <v>]
  - rebuild    --file <svg> --xml <mx.xml> [--diagram-id <id>] [--diagram-name <name>] [--width <w>] [--height <h>] [--viewBox <v>]
  - extract    --file <svg>
  - validate     --file <svg> [--shell-only] [--no-ref-checks]
  - validate-xml --file <xml> [--no-ref-checks]

Reference-backed rules (on by default) match `xml-reference.md` beside this script.

No external dependencies; uses only Python 3 stdlib.
"""

from __future__ import annotations

import argparse
import base64
import html
import os
import re
import sys
import uuid
import zlib
from collections import Counter
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import quote, unquote
from xml.etree import ElementTree as ET


# Regex patterns
CONTENT_ATTR_RE = re.compile(r'content="([^"]*)"', re.S)
DIAGRAM_RE = re.compile(r'(<diagram\b[^>]*>)(.*?)(</diagram>)', re.S)
SVG_WIDTH_RE = re.compile(r'width="([^"]+)"')
SVG_HEIGHT_RE = re.compile(r'height="([^"]+)"')
SVG_VIEWBOX_RE = re.compile(r'viewBox="([^"]+)"')


# Constants
MXFILE_TOKEN = '<mxfile'
DIAGRAM_TOKEN = '<diagram'
MXGRAPH_TOKEN = '<mxGraphModel'


def read_text(path: str) -> str:
  """Read file as UTF-8 text."""
  with open(path, 'r', encoding='utf-8') as f:
    return f.read()


def write_text(path: str, text: str) -> None:
  """Write text to file, creating parent directories if needed."""
  os.makedirs(os.path.dirname(path), exist_ok=True)
  with open(path, 'w', encoding='utf-8') as f:
    f.write(text)


def html_decode_entities(s: str) -> str:
  """Decode HTML entities (&lt; &gt; &quot; &amp; etc.)."""
  return html.unescape(s)


def html_encode_entities(s: str) -> str:
  """Encode special characters as HTML entities."""
  s = s.replace('&', '&amp;')
  s = s.replace('"', '&quot;')
  s = s.replace('<', '&lt;')
  s = s.replace('>', '&gt;')
  s = s.replace('\n', '&#10;')
  return s


def extract_content_attr(svg_text: str) -> Optional[str]:
  """Extract the content attribute value from SVG."""
  m = CONTENT_ATTR_RE.search(svg_text)
  return m.group(1) if m else None


def extract_diagram_payload(decoded_mx: str) -> Tuple[str, str, str]:
  """Extract diagram opening tag, payload, and closing tag."""
  m = DIAGRAM_RE.search(decoded_mx)
  if not m:
    raise ValueError('No <diagram> element found in content')
  return m.group(1), m.group(2), m.group(3)


def deflate_raw_base64_from_xml(xml_text: str) -> str:
  """Compress XML: encodeURIComponent -> deflateRaw -> base64."""
  pct = quote(xml_text)
  comp = zlib.compressobj(level=9, wbits=-15)
  data = comp.compress(pct.encode('utf-8')) + comp.flush()
  return base64.b64encode(data).decode('ascii')


def inflate_raw_base64_to_xml(b64_text: str) -> str:
  """Decompress: base64 -> inflateRaw -> decodeURIComponent."""
  data = base64.b64decode(b64_text)
  decompressed = zlib.decompress(data, wbits=-15)
  return unquote(decompressed.decode('utf-8'))


def parse_diagram_attr(open_tag: str, attr: str) -> Optional[str]:
  """Extract attribute value from diagram opening tag."""
  m = re.search(rf'{attr}="([^"]*)"', open_tag)
  return m.group(1) if m else None


def fresh_diagram_identity(diagram_id: Optional[str],
                           diagram_name: Optional[str],
                           file_hint: Optional[str] = None) -> Tuple[str, str]:
  """Generate fresh diagram id/name unless explicitly provided."""
  if diagram_id and diagram_name:
    return diagram_id, diagram_name
  
  # Derive slug from filename
  slug = 'diagram'
  if file_hint:
    slug = Path(file_hint).stem or slug
  slug = slug.strip() or 'diagram'
  readable = re.sub(r'[-_]+', ' ', slug).strip().title() or 'Diagram'
  
  # Generate UUID suffix
  token = uuid.uuid4().hex[:8]
  
  did = diagram_id or f'{slug}-diag-{token}'
  dname = diagram_name or f'{readable} {token}'
  return did, dname


def extract_inner_xml(xml_text: str) -> str:
  """Extract inner mxGraphModel XML from <mxfile>, <diagram>, or <mxGraphModel>."""
  xml = xml_text.strip()
  
  if xml.startswith(MXFILE_TOKEN):
    # Extract from <mxfile><diagram>PAYLOAD</diagram></mxfile>
    _, payload, _ = extract_diagram_payload(xml)
    return payload.strip()
  
  if xml.startswith(DIAGRAM_TOKEN):
    # Extract from <diagram>PAYLOAD</diagram>
    _, payload, _ = extract_diagram_payload(xml)
    return payload.strip()
  
  if xml.startswith(MXGRAPH_TOKEN):
    # Already mxGraphModel
    return xml
  
  raise ValueError('Provided XML must be <mxfile>, <diagram>, or <mxGraphModel>')


def build_minimal_svg_shell(width: int, height: int, view_box: str, content: str) -> str:
  """Build minimal SVG shell matching the working template."""
  # Parse viewBox to get dimensions for background rectangle
  vb_parts = view_box.split()
  bg_x = vb_parts[0] if len(vb_parts) >= 1 else '0'
  bg_y = vb_parts[1] if len(vb_parts) >= 2 else '0'
  bg_w = vb_parts[2] if len(vb_parts) >= 3 else str(width)
  bg_h = vb_parts[3] if len(vb_parts) >= 4 else str(height)
  
  return (
    f'<svg host="65bd71144e" xmlns="http://www.w3.org/2000/svg" '
    f'xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" '
    f'width="{width}px" height="{height}px" viewBox="{view_box}" '
    f'content="{content}" style="background-color: rgb(255, 255, 255);">\n'
    f'    <defs/>\n'
    f'    <g>\n'
    f'        <rect x="{bg_x}" y="{bg_y}" width="{bg_w}" height="{bg_h}" fill="#FFFFFF" stroke="none"/>\n'
    f'    </g>\n'
    f'</svg>'
  )


def parse_numeric_dimension(value: Optional[str]) -> Optional[int]:
  """Parse width/height value, handling 'px' suffix."""
  if not value:
    return None
  v = value.strip()
  if v.endswith('px'):
    v = v[:-2]
  try:
    return int(float(v))
  except ValueError:
    return None


def extract_svg_dimensions(svg_text: Optional[str]) -> Tuple[Optional[int], Optional[int], Optional[str]]:
  """Extract width, height, viewBox from existing SVG."""
  if not svg_text:
    return None, None, None
  
  width = None
  height = None
  view_box = None
  
  m = SVG_WIDTH_RE.search(svg_text)
  if m:
    width = parse_numeric_dimension(m.group(1))
  
  m = SVG_HEIGHT_RE.search(svg_text)
  if m:
    height = parse_numeric_dimension(m.group(1))
  
  m = SVG_VIEWBOX_RE.search(svg_text)
  if m:
    view_box = m.group(1)
  
  return width, height, view_box


def determine_canvas_dimensions(existing_svg: Optional[str],
                                width_arg: Optional[int],
                                height_arg: Optional[int],
                                view_box_arg: Optional[str]) -> Tuple[int, int, str]:
  """Determine final canvas dimensions from args or existing SVG."""
  existing_width, existing_height, existing_view_box = extract_svg_dimensions(existing_svg)
  
  width = width_arg or existing_width or 1200
  height = height_arg or existing_height or 900
  view_box = view_box_arg or existing_view_box or f'-0.5 -0.5 {width} {height}'
  
  return width, height, view_box


def decode_svg_to_xml(svg_text: str) -> str:
  """Decode mxGraph XML from SVG content attribute."""
  enc = extract_content_attr(svg_text)
  if enc is None:
    raise ValueError('Missing content attribute in <svg>')
  
  dec = html_decode_entities(enc)
  _, payload, _ = extract_diagram_payload(dec)
  
  # If payload looks like XML, return directly (uncompressed)
  if '<' in payload and '</' in payload:
    return payload
  
  # Otherwise decompress base64 payload
  return inflate_raw_base64_to_xml(payload)


def parse_mxgraph(xml_text: str) -> Tuple[Optional[ET.Element], Optional[ET.Element], Optional[str]]:
  """
  Parse mxGraph XML; return (mxGraphModel element, <root> element, error_message).
  Accepts wrapper <mxfile>, <diagram>, or bare <mxGraphModel>.
  """
  text = xml_text.strip()
  try:
    parsed = ET.fromstring(text)
  except ET.ParseError as e:
    return None, None, f'Invalid XML syntax: {e}'
  except Exception as e:
    return None, None, f'XML parsing error: {e}'

  mgm = parsed
  if mgm.tag == 'mxfile':
    d = mgm.find('diagram')
    if d is None:
      return None, None, 'mxfile missing <diagram>'
    mgm = d
  if mgm.tag == 'diagram':
    inner = mgm.find('mxGraphModel')
    if inner is None:
      return None, None, 'diagram missing <mxGraphModel>'
    mgm = inner
  if mgm.tag != 'mxGraphModel':
    return None, None, f'Root element must be <mxGraphModel> (or wrapped), found <{mgm.tag}>'

  root_el = mgm.find('root')
  if root_el is None:
    return None, None, 'Missing <root> element inside <mxGraphModel>'
  return mgm, root_el, None


def validate_mxgraph_tree(root_el: ET.Element,
                          xml_text: str,
                          *,
                          ref_checks: bool = True,
                          mxgraph_el: Optional[ET.Element] = None) -> Tuple[bool, str]:
  """
  Structural validation of <root> contents plus rules from xml-reference.md
  (vendored next to this script). Set ref_checks=False to skip reference-only rules.
  """
  errors: List[str] = []
  warnings: List[str] = []

  if ref_checks and '<!--' in xml_text:
    errors.append(
      'XML comments (<!--) are forbidden in diagram XML (xml-reference.md: CRITICAL: XML well-formedness)'
    )

  cells = root_el.findall('.//mxCell')
  graph_ids: List[str] = []
  for obj in root_el.findall('.//object'):
    oid = obj.get('id')
    if oid:
      graph_ids.append(oid)
  for cell in cells:
    cid = cell.get('id')
    if cid:
      graph_ids.append(cid)

  if ref_checks and graph_ids:
    dupes = sorted([k for k, v in Counter(graph_ids).items() if v > 1])
    if dupes:
      shown = dupes[:12]
      suffix = '…' if len(dupes) > 12 else ''
      errors.append(
        f'Duplicate id values among <mxCell>/<object> (must be unique per xml-reference.md): '
        f'{shown}{suffix}'
      )

  ids = set(graph_ids)

  xml_str = xml_text
  has0 = '<mxCell id="0"' in xml_str
  has1 = '<mxCell id="1"' in xml_str
  if not (has0 and has1):
    errors.append('Root cells id="0" and id="1" are required')

  if ref_checks:
    for cell in cells:
      if cell.get('edge') != '1':
        continue
      eid = cell.get('id') or '(no id)'
      geo = cell.find('mxGeometry')
      if geo is None:
        errors.append(
          f'Edge mxCell id={eid} missing child <mxGeometry> '
          f'(xml-reference.md: every edge must include <mxGeometry relative="1" as="geometry"/>)'
        )
        continue
      if geo.get('relative') != '1':
        errors.append(
          f'Edge mxCell id={eid} must use <mxGeometry relative="1" as="geometry"/> '
          f'(xml-reference.md: edge routing)'
        )

    for cell in cells:
      if cell.get('edge') != '1':
        continue
      geo = cell.find('mxGeometry')
      if geo is None or geo.get('relative') != '1':
        continue
      st = cell.get('style') or ''
      if 'strokeColor=' not in st:
        eid = cell.get('id') or '(no id)'
        warnings.append(
          f'Edge mxCell id={eid} has no strokeColor in style (often invisible in static SVG); '
          f'see drawio-svg-diagrams SKILL.md — Visible connectors'
        )
      val = (cell.get('value') or '').strip()
      if val and 'labelBackgroundColor=' not in st:
        eid = cell.get('id') or '(no id)'
        warnings.append(
          f'Edge mxCell id={eid} has a label but no labelBackgroundColor= in style '
          f'(labels may render with an opaque dark box in .drawio.svg); use labelBackgroundColor=none'
        )

    for cell in cells:
      if cell.get('vertex') == '1' and cell.find('mxGeometry') is None:
        vid = cell.get('id') or '(no id)'
        warnings.append(f'Vertex mxCell id={vid} has no <mxGeometry> (likely invalid; see xml-reference.md examples)')

  for cell in cells:
    if cell.get('edge') == '1':
      eid = cell.get('id')
      s, t = cell.get('source'), cell.get('target')
      if not s or not t:
        warnings.append(f'Edge {eid} missing source/target')
      elif s not in ids or t not in ids:
        warnings.append(f'Edge {eid} references unknown ids: {s}->{t}')

  for cell in cells:
    parent = cell.get('parent')
    if parent and parent not in ids:
      warnings.append(f'Cell {cell.get("id")} references unknown parent: {parent}')

  if mxgraph_el is not None and mxgraph_el.tag == 'mxGraphModel':
    bg = mxgraph_el.get('background')
    if bg != '#FFFFFF':
      warnings.append(f'background should be "#FFFFFF" for white background, found "{bg}"')

  if errors:
    return False, '; '.join(errors)
  if warnings:
    return True, 'OK (warnings: ' + '; '.join(warnings) + ')'
  return True, 'OK'


def validate_svg_shell(svg_text: str) -> Tuple[bool, str]:
  """Validate minimal SVG shell structure (content attribute format)."""
  try:
    # Check SVG has required elements
    if '<svg' not in svg_text:
      return False, 'Missing <svg> element'
    
    if '<defs/>' not in svg_text and '<defs>' not in svg_text:
      return False, 'Missing <defs> element'
    
    if '<g' not in svg_text:
      return False, 'Missing <g> element'
    
    # Check content attribute exists
    enc = extract_content_attr(svg_text)
    if enc is None:
      return False, 'Missing content attribute'
    
    # Decode and check basic structure
    dec = html_decode_entities(enc)
    if MXFILE_TOKEN not in dec:
      return False, 'content must contain <mxfile> wrapper'
    
    if DIAGRAM_TOKEN not in dec:
      return False, 'content must contain <diagram> element'
    
    m = DIAGRAM_RE.search(dec)
    if not m:
      return False, 'No <diagram> element found in content'
    
    return True, 'OK'
    
  except Exception as e:
    return False, f'Shell validation error: {e}'


def validate_svg_with_mxgraph(svg_text: str, ref_checks: bool = True) -> Tuple[bool, str]:
  """Validate SVG shell and embedded mxGraph XML structure."""
  # First validate shell
  ok, msg = validate_svg_shell(svg_text)
  if not ok:
    return ok, msg
  
  try:
    enc = extract_content_attr(svg_text)
    dec = html_decode_entities(enc)
    m = DIAGRAM_RE.search(dec)
    payload = m.group(2)
    
    # Decode payload to XML
    if '<' in payload and '</' in payload:
      xml_text = payload
    else:
      try:
        xml_text = inflate_raw_base64_to_xml(payload)
      except Exception as e:
        return False, f'Failed to decompress/URI-decode diagram payload: {e}'
    
    mgm, root_el, err = parse_mxgraph(xml_text)
    if err:
      return False, err
    assert mgm is not None and root_el is not None
    return validate_mxgraph_tree(root_el, xml_text, ref_checks=ref_checks, mxgraph_el=mgm)
    
  except Exception as e:
    return False, f'mxGraph validation error: {e}'


def validate_svg(svg_text: str, ref_checks: bool = True) -> Tuple[bool, str]:
  """Validate SVG (shell + mxGraph). Uses full validation by default."""
  return validate_svg_with_mxgraph(svg_text, ref_checks=ref_checks)


def validate_xml_file(xml_text: str, ref_checks: bool = True) -> Tuple[bool, str]:
  """Validate mxGraph XML file directly (not embedded in SVG)."""
  try:
    mgm, root_el, err = parse_mxgraph(xml_text)
    if err:
      return False, err
    assert mgm is not None and root_el is not None
    return validate_mxgraph_tree(root_el, xml_text, ref_checks=ref_checks, mxgraph_el=mgm)
  except Exception as e:
    return False, f'XML validation error: {e}'


def cmd_init_empty(args):
  """Create a new empty .drawio.svg with minimal mxGraphModel."""
  # Minimal valid mxGraphModel skeleton
  mx = (
    '<mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" '
    'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="850" '
    'pageHeight="1100" background="#FFFFFF" math="0" shadow="0">'
    '<root>'
    '<mxCell id="0"/>'
    '<mxCell id="1" parent="0"/>'
    '</root>'
    '</mxGraphModel>'
  )
  
  diag_id, diag_name = fresh_diagram_identity(args.diagram_id, args.diagram_name, args.file)
  width, height, view_box = determine_canvas_dimensions(None, args.width, args.height, args.viewBox)
  
  b64 = deflate_raw_base64_from_xml(mx)
  mxfile = f'<mxfile><diagram id="{diag_id}" name="{diag_name}">{b64}</diagram></mxfile>'
  encoded = html_encode_entities(mxfile)
  
  svg = build_minimal_svg_shell(width, height, view_box, encoded)
  write_text(args.file, svg)
  print(f'Initialized empty diagram: {args.file}')


def cmd_rebuild(args):
  """Rebuild SVG shell around provided mxGraph XML."""
  xml_text = read_text(args.xml)
  inner_xml = extract_inner_xml(xml_text)
  
  diag_id, diag_name = fresh_diagram_identity(args.diagram_id, args.diagram_name, args.file)
  
  # Read dimensions from existing file if it exists (before deleting)
  existing_svg = read_text(args.file) if os.path.exists(args.file) else None
  width, height, view_box = determine_canvas_dimensions(existing_svg, args.width, args.height, args.viewBox)
  
  # Delete existing file to ensure clean rebuild (prevents caching issues)
  if os.path.exists(args.file):
    os.remove(args.file)
  
  b64 = deflate_raw_base64_from_xml(inner_xml)
  mxfile = f'<mxfile><diagram id="{diag_id}" name="{diag_name}">{b64}</diagram></mxfile>'
  encoded = html_encode_entities(mxfile)
  
  svg = build_minimal_svg_shell(width, height, view_box, encoded)
  write_text(args.file, svg)
  print(f'Rebuilt: {args.file}')

  # Best-effort cleanup of temporary XML models so we always start fresh next time.
  # Simplified rule: if the XML used for rebuild lives in the *same folder* as the SVG
  # and follows the sidecar pattern "<name>.model.xml", delete it.
  try:
    svg_path = Path(args.file)
    xml_path = Path(args.xml)

    if (xml_path.parent == svg_path.parent
        and xml_path.suffix == '.xml'
        and xml_path.name.endswith('.model.xml')
        and xml_path.is_file()):
      xml_path.unlink()
  except Exception:
    # Cleanup is non-critical; ignore any errors here.
    pass


def cmd_extract(args):
  """Extract and print decoded mxGraph XML."""
  svg = read_text(args.file)
  xml = decode_svg_to_xml(svg)
  sys.stdout.write(xml)


def cmd_validate(args):
  """Validate SVG content and XML structure."""
  svg = read_text(args.file)
  
  if getattr(args, 'shell_only', False):
    ok, msg = validate_svg_shell(svg)
  else:
    ref = not getattr(args, 'no_ref_checks', False)
    ok, msg = validate_svg_with_mxgraph(svg, ref_checks=ref)
  
  if ok:
    print('OK')
    sys.exit(0)
  else:
    print(f'INVALID: {msg}')
    sys.exit(1)


def cmd_validate_xml(args):
  """Validate mxGraph XML file directly."""
  xml = read_text(args.file)
  ref = not getattr(args, 'no_ref_checks', False)
  ok, msg = validate_xml_file(xml, ref_checks=ref)
  
  if ok:
    print('OK')
    sys.exit(0)
  else:
    print(f'INVALID: {msg}')
    sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
  """Build command-line argument parser."""
  p = argparse.ArgumentParser(
    description='draw.io SVG helper (minimal shell + compressed mxGraph model)'
  )
  sub = p.add_subparsers(dest='cmd', required=True)
  
  ie = sub.add_parser('init-empty', help='Create a new empty .drawio.svg')
  ie.add_argument('--file', required=True)
  ie.add_argument('--diagram-id', help='Override auto-generated diagram id')
  ie.add_argument('--diagram-name', help='Override auto-generated diagram name')
  ie.add_argument('--width', type=int, help='Canvas width (default: 1200)')
  ie.add_argument('--height', type=int, help='Canvas height (default: 900)')
  ie.add_argument('--viewBox', help='viewBox value (default: -0.5 -0.5 {width} {height})')
  ie.set_defaults(func=cmd_init_empty)
  
  rb = sub.add_parser('rebuild', help='Rebuild SVG shell around provided mxGraph XML')
  rb.add_argument('--file', required=True)
  rb.add_argument('--xml', required=True, help='Path to XML file (<mxfile>, <diagram>, or <mxGraphModel>)')
  rb.add_argument('--diagram-id', help='Override auto-generated diagram id')
  rb.add_argument('--diagram-name', help='Override auto-generated diagram name')
  rb.add_argument('--width', type=int, help='Canvas width (inherits from existing SVG if not provided)')
  rb.add_argument('--height', type=int, help='Canvas height (inherits from existing SVG if not provided)')
  rb.add_argument('--viewBox', help='viewBox value (inherits from existing SVG if not provided)')
  rb.set_defaults(func=cmd_rebuild)
  
  e = sub.add_parser('extract', help='Extract and print decoded mxGraph XML')
  e.add_argument('--file', required=True)
  e.set_defaults(func=cmd_extract)
  
  v = sub.add_parser('validate', help='Validate SVG content and XML structure')
  v.add_argument('--file', required=True)
  v.add_argument('--shell-only', action='store_true',
                 help='Only validate SVG shell structure (skip mxGraph XML validation)')
  v.add_argument('--no-ref-checks', action='store_true',
                 help='Skip xml-reference.md rules (XML comments, duplicate ids, edge <mxGeometry>)')
  v.set_defaults(func=cmd_validate)
  
  vx = sub.add_parser('validate-xml', help='Validate mxGraph XML file directly')
  vx.add_argument('--file', required=True, help='Path to XML file (<mxfile>, <diagram>, or <mxGraphModel>)')
  vx.add_argument('--no-ref-checks', action='store_true',
                  help='Skip xml-reference.md rules (XML comments, duplicate ids, edge <mxGeometry>)')
  vx.set_defaults(func=cmd_validate_xml)
  
  return p


def main(argv=None):
  parser = build_parser()
  args = parser.parse_args(argv)
  args.func(args)


def run_tests():
  """Run comprehensive tests to verify all functionality works correctly."""
  import tempfile
  import shutil
  
  print("Running drawio_svg.py tests...")
  failures = []
  tests_run = 0
  
  def assert_test(condition: bool, message: str):
    nonlocal tests_run
    tests_run += 1
    if not condition:
      failures.append(f"FAIL: {message}")
      print(f"  ✗ {message}")
    else:
      print(f"  ✓ {message}")
  
  # Test 1: HTML entity encoding/decoding (round-trip)
  test_xml = '<mxGraphModel><root><mxCell id="0"/></root></mxGraphModel>'
  encoded = html_encode_entities(test_xml)
  decoded = html_decode_entities(encoded)
  assert_test(decoded == test_xml, "HTML entity encoding/decoding round-trip")
  assert_test('&lt;' in encoded and '&gt;' in encoded, "HTML entities are encoded")
  
  # Test 2: Base64 compression/decompression (round-trip)
  compressed = deflate_raw_base64_from_xml(test_xml)
  decompressed = inflate_raw_base64_to_xml(compressed)
  assert_test(decompressed == test_xml, "Base64 compression/decompression round-trip")
  assert_test(len(compressed) > 0, "Compression produces output")
  
  # Test 3: Content attribute extraction
  svg_with_content = '<svg content="&lt;mxfile&gt;&lt;diagram&gt;test&lt;/diagram&gt;&lt;/mxfile&gt;"></svg>'
  content = extract_content_attr(svg_with_content)
  assert_test(content is not None, "Content attribute extraction")
  assert_test('&lt;mxfile&gt;' in content, "Content contains encoded mxfile")
  
  svg_no_content = '<svg></svg>'
  content_none = extract_content_attr(svg_no_content)
  assert_test(content_none is None, "Missing content attribute returns None")
  
  # Test 4: Diagram payload extraction
  mxfile_text = '<mxfile><diagram id="d" name="P">payload</diagram></mxfile>'
  open_tag, payload, close_tag = extract_diagram_payload(mxfile_text)
  assert_test(payload == 'payload', "Diagram payload extraction")
  assert_test('id="d"' in open_tag, "Diagram attributes preserved")
  
  # Test 5: Inner XML extraction from different formats
  mxgraph_xml = '<mxGraphModel><root><mxCell id="0"/></root></mxGraphModel>'
  diagram_xml = f'<diagram>{mxgraph_xml}</diagram>'
  mxfile_xml = f'<mxfile>{diagram_xml}</mxfile>'
  
  inner1 = extract_inner_xml(mxgraph_xml)
  inner2 = extract_inner_xml(diagram_xml)
  inner3 = extract_inner_xml(mxfile_xml)
  assert_test(inner1 == mxgraph_xml, "Extract inner XML from mxGraphModel")
  assert_test(inner2 == mxgraph_xml, "Extract inner XML from diagram")
  assert_test(inner3 == mxgraph_xml, "Extract inner XML from mxfile")
  
  # Test 6: SVG shell building
  shell = build_minimal_svg_shell(1200, 900, '-0.5 -0.5 1200 900', 'test-content')
  assert_test('<svg' in shell, "SVG shell contains svg tag")
  assert_test('<defs/>' in shell, "SVG shell contains defs")
  assert_test('<g>' in shell, "SVG shell contains g element")
  assert_test('width="1200px"' in shell, "SVG shell has correct width")
  assert_test('height="900px"' in shell, "SVG shell has correct height")
  assert_test('viewBox="-0.5 -0.5 1200 900"' in shell, "SVG shell has correct viewBox")
  assert_test('content="test-content"' in shell, "SVG shell has content attribute")
  assert_test('background-color: rgb(255, 255, 255)' in shell, "SVG shell has white background")
  assert_test('<rect' in shell and 'fill="#FFFFFF"' in shell, "SVG shell has white background rectangle")
  
  # Test 7: Dimension parsing
  assert_test(parse_numeric_dimension('1200px') == 1200, "Parse dimension with px suffix")
  assert_test(parse_numeric_dimension('900') == 900, "Parse dimension without suffix")
  assert_test(parse_numeric_dimension('1200.5px') == 1200, "Parse float dimension")
  assert_test(parse_numeric_dimension(None) is None, "Parse None dimension")
  
  # Test 8: SVG dimension extraction
  svg_dims = '<svg width="1200px" height="900px" viewBox="-0.5 -0.5 1200 900"></svg>'
  w, h, vb = extract_svg_dimensions(svg_dims)
  assert_test(w == 1200, "Extract SVG width")
  assert_test(h == 900, "Extract SVG height")
  assert_test(vb == '-0.5 -0.5 1200 900', "Extract SVG viewBox")
  
  # Test 9: Canvas dimension determination
  w2, h2, vb2 = determine_canvas_dimensions(None, None, None, None)
  assert_test(w2 == 1200, "Default width is 1200")
  assert_test(h2 == 900, "Default height is 900")
  
  w3, h3, vb3 = determine_canvas_dimensions(svg_dims, None, None, None)
  assert_test(w3 == 1200, "Inherit width from existing SVG")
  assert_test(h3 == 900, "Inherit height from existing SVG")
  
  w4, h4, vb4 = determine_canvas_dimensions(None, 800, 600, None)
  assert_test(w4 == 800, "Use provided width")
  assert_test(h4 == 600, "Use provided height")
  
  # Test 10: Fresh diagram identity generation
  did1, dname1 = fresh_diagram_identity(None, None, 'test-file.drawio.svg')
  did2, dname2 = fresh_diagram_identity(None, None, 'test-file.drawio.svg')
  assert_test(did1 != did2, "Fresh diagram IDs are unique")
  assert_test('test-file' in did1.lower(), "Diagram ID derived from filename")
  
  did3, dname3 = fresh_diagram_identity('custom-id', 'Custom Name', None)
  assert_test(did3 == 'custom-id', "Use provided diagram ID")
  assert_test(dname3 == 'Custom Name', "Use provided diagram name")
  
  # Test 11: XML validation
  valid_xml = '<mxGraphModel dx="1200" dy="800" grid="1" background="#FFFFFF"><root><mxCell id="0"/><mxCell id="1" parent="0"/></root></mxGraphModel>'
  ok, msg = validate_xml_file(valid_xml)
  assert_test(ok, f"Valid XML passes validation: {msg}")
  
  invalid_xml_no_root = '<mxGraphModel><root></root></mxGraphModel>'
  ok2, msg2 = validate_xml_file(invalid_xml_no_root)
  assert_test(not ok2, "XML without id=0 and id=1 fails validation")
  
  invalid_xml_no_model = '<root><mxCell id="0"/></root>'
  ok3, msg3 = validate_xml_file(invalid_xml_no_model)
  assert_test(not ok3, "XML without mxGraphModel fails validation")
  
  # Test 12: SVG shell validation
  minimal_svg = '<svg><defs/><g><rect/></g></svg>'
  ok4, msg4 = validate_svg_shell(minimal_svg)
  assert_test(not ok4, "SVG without content attribute fails shell validation")
  
  # Test 13: Full workflow test with temporary files
  with tempfile.TemporaryDirectory() as tmpdir:
    test_svg = os.path.join(tmpdir, 'test.drawio.svg')
    test_xml_file = os.path.join(tmpdir, 'test.model.xml')
    
    # Create minimal valid XML
    valid_mxgraph = '<mxGraphModel dx="1200" dy="800" grid="1" background="#FFFFFF"><root><mxCell id="0"/><mxCell id="1" parent="0"/></root></mxGraphModel>'
    write_text(test_xml_file, valid_mxgraph)
    
    # Test init-empty
    class EmptyArgs:
      file = test_svg
      diagram_id = 'test-id'
      diagram_name = 'Test'
      width = 1200
      height = 900
      viewBox = None
    
    cmd_init_empty(EmptyArgs())
    assert_test(os.path.exists(test_svg), "init-empty creates file")
    svg_content = read_text(test_svg)
    assert_test('<svg' in svg_content, "init-empty creates valid SVG")
    assert_test('content=' in svg_content, "init-empty includes content attribute")
    
    # Test extract
    class ExtractArgs:
      file = test_svg
    
    import io
    import contextlib
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
      cmd_extract(ExtractArgs())
    extracted = f.getvalue()
    assert_test('<mxGraphModel' in extracted, "extract returns mxGraphModel")
    assert_test('id="0"' in extracted, "extract includes root cells")
    
    # Test rebuild
    rebuild_svg = os.path.join(tmpdir, 'rebuild.drawio.svg')
    class RebuildArgs:
      file = rebuild_svg
      xml = test_xml_file
      diagram_id = None
      diagram_name = None
      width = 1200
      height = 900
      viewBox = None
    
    cmd_rebuild(RebuildArgs())
    assert_test(os.path.exists(rebuild_svg), "rebuild creates file")
    rebuild_content = read_text(rebuild_svg)
    assert_test('<svg' in rebuild_content, "rebuild creates valid SVG")
    
    # After rebuild, the sidecar model XML in the same folder should be cleaned up.
    assert_test(not os.path.exists(test_xml_file), "rebuild deletes sidecar .model.xml in same folder")
    
    # Test validate functions directly
    rebuild_content_for_validate = read_text(rebuild_svg)
    ok6, msg6 = validate_svg_shell(rebuild_content_for_validate)
    assert_test(ok6, f"SVG shell validation passes: {msg6}")
    
    ok7, msg7 = validate_svg_with_mxgraph(rebuild_content_for_validate)
    assert_test(ok7, f"Full SVG validation passes: {msg7}")
    
    # validate_xml_file works on the original XML content
    ok8, msg8 = validate_xml_file(valid_mxgraph)
    assert_test(ok8, f"XML validation passes: {msg8}")
  
  # Test 14: Decode SVG to XML (full round-trip)
  test_mxgraph = '<mxGraphModel dx="1200" background="#FFFFFF"><root><mxCell id="0"/><mxCell id="1" parent="0"/></root></mxGraphModel>'
  b64 = deflate_raw_base64_from_xml(test_mxgraph)
  mxfile_wrapped = f'<mxfile><diagram id="test" name="Test">{b64}</diagram></mxfile>'
  encoded_content = html_encode_entities(mxfile_wrapped)
  test_svg_full = f'<svg content="{encoded_content}"><defs/><g/></svg>'
  
  decoded_xml = decode_svg_to_xml(test_svg_full)
  assert_test(decoded_xml == test_mxgraph, "Full SVG decode round-trip works")
  
  # Test 15: Validate SVG with mxGraph
  ok5, msg5 = validate_svg_with_mxgraph(test_svg_full)
  assert_test(ok5, f"Full SVG validation passes: {msg5}")
  
  # Test 16: xml-reference.md — edge must have <mxGeometry relative="1">
  good_edge_xml = (
    '<mxGraphModel background="#FFFFFF"><root>'
    '<mxCell id="0"/><mxCell id="1" parent="0"/>'
    '<mxCell id="2" style="rounded=1;" vertex="1" parent="1">'
    '<mxGeometry x="10" y="10" width="80" height="40" as="geometry"/></mxCell>'
    '<mxCell id="3" style="rounded=1;" vertex="1" parent="1">'
    '<mxGeometry x="200" y="10" width="80" height="40" as="geometry"/></mxCell>'
    '<mxCell id="e1" edge="1" parent="1" source="2" target="3" style="edgeStyle=orthogonalEdgeStyle;">'
    '<mxGeometry relative="1" as="geometry"/></mxCell>'
    '</root></mxGraphModel>'
  )
  ok_ge, msg_ge = validate_xml_file(good_edge_xml)
  assert_test(ok_ge, f'Edge with mxGeometry passes reference checks: {msg_ge}')
  
  bad_edge_xml = (
    '<mxGraphModel background="#FFFFFF"><root>'
    '<mxCell id="0"/><mxCell id="1" parent="0"/>'
    '<mxCell id="2" vertex="1" parent="1"><mxGeometry x="0" y="0" width="10" height="10" as="geometry"/></mxCell>'
    '<mxCell id="3" vertex="1" parent="1"><mxGeometry x="50" y="0" width="10" height="10" as="geometry"/></mxCell>'
    '<mxCell id="e1" edge="1" parent="1" source="2" target="3"/>'
    '</root></mxGraphModel>'
  )
  ok_be, msg_be = validate_xml_file(bad_edge_xml)
  assert_test(not ok_be, f'Self-closing edge without mxGeometry must fail: {msg_be}')
  
  # Test 17: xml-reference.md — no XML comments in diagram XML
  comment_xml = (
    '<mxGraphModel background="#FFFFFF"><!-- bad -->'
    '<root><mxCell id="0"/><mxCell id="1" parent="0"/></root></mxGraphModel>'
  )
  ok_cm, msg_cm = validate_xml_file(comment_xml)
  assert_test(not ok_cm, f'XML comment must fail reference check: {msg_cm}')
  ok_cm2, msg_cm2 = validate_xml_file(comment_xml, ref_checks=False)
  assert_test(ok_cm2, f'XML comment allowed when ref checks off: {msg_cm2}')
  
  # Test 18: duplicate mxCell ids
  dupe_xml = (
    '<mxGraphModel background="#FFFFFF"><root>'
    '<mxCell id="0"/><mxCell id="1" parent="0"/>'
    '<mxCell id="2" vertex="1" parent="1"><mxGeometry x="0" y="0" width="1" height="1" as="geometry"/></mxCell>'
    '<mxCell id="2" vertex="1" parent="1"><mxGeometry x="10" y="0" width="1" height="1" as="geometry"/></mxCell>'
    '</root></mxGraphModel>'
  )
  ok_dp, msg_dp = validate_xml_file(dupe_xml)
  assert_test(not ok_dp, f'Duplicate ids must fail: {msg_dp}')
  
  print(f"\nTests completed: {tests_run} tests run, {len(failures)} failures")
  
  if failures:
    print("\nFailures:")
    for failure in failures:
      print(f"  {failure}")
    return False
  
  print("All tests passed! ✓")
  return True


if __name__ == '__main__':
  if len(sys.argv) > 1 and sys.argv[1] == '--test':
    success = run_tests()
    sys.exit(0 if success else 1)
  main()
