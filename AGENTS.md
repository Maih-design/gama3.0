# AGENTS.md

## 1. Project Context
- Read PROJECT_OVERVIEW.md before starting any task.
- Treat the existing source code as the primary reference.
- Do not assume that previous project structures or implementations still apply.

## 2. Development Workflow
- Work incrementally, one task at a time.
- Inspect relevant existing files before proposing changes.
- Explain the proposed changes before implementing them.
- Do not modify files until the user explicitly approves the proposed changes.
- After implementation, show a summary of modified files and explain the changes.

## 3. Architecture Rules
- Follow the existing project architecture and coding conventions.
- Avoid unnecessary new applications, models, fields, or dependencies.
- Keep business logic separate from views.
- Put business operations and calculations in operations.py where appropriate.
- Do not duplicate existing shared models or functionality.
- Reuse existing models whenever appropriate.

## 4. Existing System Protection
- The existing Gamma Knife system is operational and must remain functional.
- Do not change existing Gamma Knife workflows unless explicitly requested.
- New Bone Marrow Transplant and ATG functionality must not break existing functionality.
- Do not refactor unrelated code.

## 5. Database Safety
- Never delete, replace, reset, or overwrite the database.
- Never modify or delete existing migrations without explicit approval.
- Do not run migrations without explicit approval.
- Do not use real patient records in testing.
- Preserve existing data and database relationships.

## 6. Testing
- Run appropriate checks after approved changes.
- Do not modify unrelated files to fix warnings.
- Report errors clearly instead of silently changing unrelated code.

## 7. Communication
- Communicate in Arabic.
- Explain technical concepts simply and directly.
- Avoid unnecessary complexity and overengineering.
- Ask only when an important business rule or design decision is unclear.
- Never invent requirements or assume medical or financial rules.
