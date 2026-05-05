# Coding Standards and Best Practices

## General Principles

### Code Quality
- Write self-documenting code with clear variable/function names
- Keep functions small and focused (single responsibility principle)
- Avoid deep nesting (max 3 levels)
- No magic numbers - use named constants

### Comments
- Write comments for "why", not "what"
- Document complex algorithms
- Keep comments up-to-date with code changes
- Remove commented-out code before committing

## Language-Specific Standards

### Python
- **Follow PEP 8:** Use 4 spaces for indentation.
- **Naming Conventions:**
    - Modules: `lowercase_with_underscores`
    - Packages: `lowercase`
    - Classes: `CapWords` (CamelCase)
    - Functions/Variables: `lowercase_with_underscores`
    - Constants: `ALL_CAPS_WITH_UNDERSCORES`
- **Docstrings:** Use docstrings for all modules, classes, and public functions (PEP 257 format).
- **Imports:**
    - Place imports at the top of the file.
    - Group imports in this order: standard library, third-party, local application/library.
    - Separate groups with a blank line.
- **Line Length:** Limit lines to a maximum of **79 characters**.
- **Whitespace:**
    - Use blank lines sparingly to separate logical sections.
    - Avoid extraneous whitespace in expressions (e.g., `a = b + c` is preferred over `a = b + c`).
- **Function/Method Arguments:** Explicitly pass `self` as the first argument to instance methods. Use `cls` for class methods.

### JavaScript
- Use **ES6+** features.
- Prefer **const** and **let** over `var`.
- Use **semicolons** consistently.
- Use **CamelCase** for variables and functions.
- Use **PascalCase** for classes and components.
- Use **JSDoc** for documentation.

### SQL
- Use **ALL CAPS** for SQL keywords (e.g., SELECT, FROM, WHERE).
- Use **lowercase_with_underscores** for table and column names.
- Always use **prepared statements** to prevent SQL injection.
- Alias columns and tables to improve readability.
