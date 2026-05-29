# Codebase Architecture Documentation Generator

Generate comprehensive architecture documentation by analyzing the repository structure, code patterns, and system design. Create a detailed `architecture.md` file in the `docs/` folder.

## Analysis Framework

**CRITICAL FIRST STEP: Read README.md**

Before generating any documentation, **ALWAYS** read the README.md file to understand what's already documented:

- Technology stack and frameworks (likely comprehensive)
- High-level architecture overview
- Basic project structure (directory navigation)
- Development setup and prerequisites
- API documentation and endpoints
- Business functions and features
- Technical capabilities and configuration examples

**Primary Objectives:**

- Analyze code organization principles and architectural patterns
- Create detailed component interaction diagrams and data flow visualizations
- Document design decisions and architectural reasoning behind the structure
- Provide deep architectural insights that complement README.md's overview
- Focus on layer separation, dependency management, and system boundaries
- Explain how the codebase structure supports scalability and maintainability

## Documentation Requirements

### 🏗️ **System Architecture**

- Create **Mermaid diagrams** visualizing the core architecture layers
- Show component interactions, data flow, and system boundaries
- Include external dependencies and integration points
- Generate **domain model diagrams** from actual database migration files and jOOQ generated classes

### 📁 **Detailed Project Structure**

- Provide **complete project structure from root level** in one place without external references
- Use **pattern-based descriptions with wildcards** (*.java,*Test.java, *Config.java) instead of individual file listings
- Use **visual hierarchy with emojis** to group related components and show directory structure
- **Start from project root** and show complete directory tree with patterns
- **Use wildcards for file naming conventions**: `*Controller.java`, `*Service.java`, `*Test.java`
- **Group similar files with patterns**: `tables/*.java`, `api/*Api.java`, `records/*Record.java`
- **Include all major directories**: src/, database/, docs/, build configuration
- Explain **architectural patterns** behind the organization (package-by-feature, layer separation)
- Document **naming conventions** and organizational principles
- **Focus on structural patterns rather than individual file inventory**

### ⚙️ **Design Patterns & Architectural Decisions**

- **ASSUME README.md has comprehensive technology stack** - reference it instead of duplicating
- Focus on architectural patterns (layered architecture, dependency injection, etc.)
- Document design decisions and their rationale
- Explain code organization principles and conventions
- Detail how different architectural patterns work together
- Analyze framework usage patterns and custom implementations
- **AVOID technology version lists** - README.md covers this comprehensively

### 🔄 **Data Flow & Component Interactions**

- Map request/response cycles through the system
- Document API endpoints and their relationships
- Show how different layers communicate
- Explain event handling and asynchronous processing

### 🗄️ **Domain Model Analysis**

- **Extract domain model from actual codebase** - analyze database migration files (`database/migration/`) and jOOQ generated classes (`src/generated/java/jooq/`)
- **Read migration scripts** to identify actual tables, foreign keys, and constraints
- **Analyze jOOQ generated table classes** to understand entity structure and relationships
- **IF multiple tables with relationships exist**: Create ER diagrams showing entity relationships and foreign keys
- **IF only single entity exists**: Create simple ER diagram with single entity box (no field details)
- **Use actual table names** and relationships as defined in the schema
- **Focus on domain boundaries and business rules** rather than database implementation details
- **Show database constraints** (foreign keys, unique constraints) that enforce business rules
- **Reference migration files** for schema details without duplicating SQL content
- **Emphasize domain architecture patterns** over database schema visualization

### 🎯 **Architecture Decisions**

- **Extract architectural decisions** from code patterns and configuration choices
- **Look for unique design choices** that deviate from standard frameworks
- **Document technology selection rationale** when evident from implementation
- **Identify trade-offs** made in the codebase (e.g., jOOQ vs JPA, stateless vs stateful)
- **If no unique decisions are evident**, provide placeholder template for future ADRs
- **Include decision context** and alternatives considered when discoverable from code/comments

### 🚀 **Development Information**

- **Reference README.md for setup instructions** instead of duplicating
- Focus on architecture-specific development considerations and patterns
- Include code generation dependencies and architectural build requirements
- Document testing architecture patterns and observability considerations
- Cover performance considerations specific to the architectural choices

## Output File Structure

Create `docs/architecture.md` with the following sections:

```markdown
# System Architecture

## Overview
[High-level system purpose and scope]

## Architecture Diagram
[Mermaid diagram of system architecture]

------------

## Project Structure
[Complete project structure from root level using pattern-based descriptions with wildcards]
[Use emojis and visual hierarchy - start from project root directory]
[Group files with patterns: *Config.java, *Controller.java, *Service.java, *Test.java]
[Include all major directories: src/, database/, docs/, build files]
[Add "Architectural Patterns" section explaining organization principles]

------------

## Design Patterns & Architectural Decisions
[Reference: "See [README.md Technology Map](../README.md#technology-map) for complete technology stack"]
[Focus on architectural patterns, design decisions, and code organization principles]

------------

## Component Interactions
[Data flow diagrams and component relationships - ensure Mermaid syntax is correct with proper quotes and arrow types]

## API Architecture
[API structure and endpoint organization]

------------

## Domain Model Architecture
[Extract actual entities from database migration files and jOOQ generated classes]
[IF multiple tables with relationships: Create ER diagrams showing entity relationships]
[IF single entity: Create simple ER diagram with single entity box (no field details)]
[Focus on domain boundaries and business rules rather than database schema details]

------------

## Architecture Decisions
[Document key architectural decisions found in the codebase with rationale - if none are evident, include placeholder with guidance]

------------

## Development Notes
[Reference README.md for setup - focus on architecture-specific development considerations, code generation, testing patterns, and performance considerations]

------------

## Learning Resources
[Relevant articles and similar projects]
```

## Implementation Guidelines

✅ **READ README.md FIRST** - assume it contains comprehensive technology stack and development setup  
✅ **AVOID DUPLICATION** - reference README.md for technology stack and setup, focus on architectural insights  
✅ **CREATE SELF-CONTAINED STRUCTURE** - provide complete project structure without external references  
✅ **USE PATTERN-BASED DESCRIPTIONS** - wildcards and emojis instead of exhaustive file listings  
✅ **USE MERMAID DIAGRAMS** extensively - ensure correct syntax with proper quotes and arrow types  
✅ **FOCUS ON DOMAIN ARCHITECTURE** - entity relationships without field details, reference migration files  
✅ **ANALYZE CODE ORGANIZATION** - explain architectural patterns and design decisions  
✅ **DOCUMENT ARCHITECTURAL DECISIONS** - extract decisions from codebase with evidence and rationale  
✅ **REMOVE DEEP DIVE SECTIONS** - keep content focused and complete without trailing promises

## Quality Guidelines

Ensure the generated documentation:

- **Maintains Focus**: Each section provides architectural value without duplication
- **Uses Correct Syntax**: All Mermaid diagrams render without parse errors
- **Stays Current**: Pattern-based descriptions that won't become outdated
- **Provides Value**: Architectural insights that help developers understand design decisions
- **Remains Complete**: Self-contained sections that don't require external references
- **Follows Conventions**: Consistent structure and clear architectural reasoning
