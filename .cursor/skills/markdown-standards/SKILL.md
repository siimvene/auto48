---
name: markdown-standards
description: Markdown formatting standards for documentation and rule files. Use when creating, editing, or reviewing Markdown files (.md, .mdc), or when the user asks about markdown formatting best practices.
---

# Markdown Documentation Standards

## Requirements

- Follow the official Markdown Guide for all basic and extended syntax
- Maintain clear document structure with proper heading hierarchy
- Include appropriate YAML front matter for metadata when required
- Maximum heading depth: 4 levels
- Indent content within XML tags by 2 spaces
- Keep tables simple and readable with proper alignment

## Critical Formatting Rules

### Headings (MD022, MD026, MD024)

- **ALWAYS** add blank line before and after headings
- Use ATX-style headings with space after hash: `# Heading`
- Maintain proper heading hierarchy (don't skip levels)
- **NEVER** use trailing punctuation in headings (no colons, periods, exclamation marks)
- **NEVER** use duplicate heading content within the same document

### Lists (MD032, MD029)

- **ALWAYS** surround lists with blank lines
- Use **sequential numbering** for ordered lists: 1, 2, 3 (NOT 4, 5, 6 or 1, 1, 1)
- Start ordered lists with 1

### Tables (MD058)

- **ALWAYS** surround tables with blank lines
- Use proper alignment indicators: `:---`, `:---:`, `---:`

### Code Blocks (MD031, MD040, MD038)

- **ALWAYS** surround fenced code blocks with blank lines
- **ALWAYS** specify language for code blocks: `typescript`, `bash`, `yaml`
- Never use bare ``` without language specification
- **NEVER** use spaces inside code span elements: `code` not ` code `

### Links and References (MD051, MD033)

- **ALWAYS** validate internal link fragments (anchors)
- Ensure linked sections/headings actually exist
- Use markdown links instead of HTML `<a>` tags when possible

### File Structure (MD047, MD009)

- **ALWAYS** end files with single newline character
- **NEVER** use trailing spaces (except for line breaks with 2 spaces)

### Emphasis vs Headings (MD036)

- **NEVER** use emphasis (bold/italic) as heading replacement
- Use proper heading levels instead of **Bold Text**

### HTML Elements (MD033)

- Avoid inline HTML when possible
- Only use HTML for complex structures not supported in markdown

## Examples

**Good:**

```markdown
# Document Title

## Section Heading

Content with **bold text** and _italics_.

### Subsection

Here is a list with proper spacing:

- First item
- Second item

Here is a properly numbered ordered list:

1. First step
2. Second step
3. Third step

| Name |  Type  | Description |
| :--- | :----: | ----------: |
| id   | number | Primary key |
| name | string | User's name |

Code example with language specified:

```typescript
function example(): void {
  console.log("Hello, Universe!");
}
```

Valid internal link: [See examples](#examples)
```

**Bad:**

```markdown
# Incorrect Heading:
content without proper spacing

### Another heading!
- List without spacing
- Second item

4. Starting with wrong number
5. Continuing incorrectly

|| No | spacing | around ||

```
function withoutLanguageSpecified() {}
```

<a href="#nonexistent">Broken link</a>
```

## Summary of Critical Rules

- ATX-style headings with space after hash, no trailing punctuation
- Proper heading hierarchy (don't skip levels)
- Blank line before and after headings, lists, tables, and code blocks
- Sequential numbering for ordered lists starting with 1
- Always specify language in fenced code blocks
- Validate all internal link fragments
- End files with exactly one newline
- Never use bold/italic as heading replacements
- Use markdown links instead of HTML when possible
- Close XML tags on their own line at the parent indentation level
