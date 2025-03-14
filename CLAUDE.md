# OAUTH3-TEE-PROXY DEVELOPMENT GUIDE

## WORKFLOW
- Commit early and often - don't wait for user instructions to commit changes
- Keep changes focused on single issues or features per commit
- Write descriptive commit messages explaining what and why (not how)
- Always run tests before committing if possible
- Push changes to remote branches when ready for review

## COMMANDS
- Run service: `uvicorn main:app --reload --host 0.0.0.0 --port 8000`
- Docker setup: `docker-compose up --build`
- Install deps: `pip install -r requirements.txt`
- Suggested linting: `ruff check .`
- Suggested formatting: `black .`
- Suggested type checking: `mypy .`
- Run tests: `pytest`
- Run single test: `pytest tests/test_file.py::test_function -v`

## CODE STYLE
- Imports order: stdlib → third-party → local
- Use type hints consistently for all functions and method signatures
- Naming: snake_case for variables/functions, PascalCase for classes
- Error handling with specific exception types and proper logging
- Async/await for I/O operations
- SQLAlchemy models with UUID primary keys
- Pydantic models for request/response validation
- FastAPI dependency injection with Depends()
- Security: WebAuthn, OAuth2 tokens, env-based configuration
- Templates: Jinja2 with HTML/CSS/JS in dedicated directories
- Organize functions alphabetically by function name within the same file or scope
- Router files should only contain route definitions, request validation, and dependency injection - business logic belongs in separate modules

## AUTHENTICATION PRINCIPLES
- Maintain a strong separation of concerns with dedicated modules for authentication logic
- Use JWT tokens for authentication with appropriate expiration (2 hours default)
- Store only essential data in JWT payload (user_id, policy, token_id)
- Include proper token rotation with 30-minute buffer for session tokens
- Always log authentication events for user visibility and security
- Implement proper revocation mechanisms for all authentication tokens
- Keep WebAuthn/passkey implementation clean with clear business logic separation
- Document all security decisions and authentication flow comprehensively
- Follow SOLID principles for all authentication-related code
- Minimize JWT payload size and never include sensitive user information

## PLUGIN ARCHITECTURE
- Each integration should be implemented as a plugin with these components:
  - Authorization plugin: Handles authentication with resource servers
  - Resource plugin: Handles interactions with the resource server API
- Plugins should implement standard interfaces:
  - `AuthorizationPlugin`: Authentication flow with resource servers
  - `ResourcePlugin`: Resource server API interaction
- Plugin registration via entry points in setup.py
- Plugin configuration via environment variables or config file

## TESTING PRINCIPLES
- NEVER add test-specific code to production codebase
- Tests should be aware of the code, not vice versa
- If the production behavior has NOT been recently modified, assume the test is correct and fix the behavior
- Only update tests to match production behavior when you've intentionally changed that behavior
- Ask the user if unsure whether to change tests or production code
- If tests require special handling, implement it in test fixtures or helpers
- Use mocks and patch appropriately to simulate different behaviors
- Maintain clear separation between test and production environments