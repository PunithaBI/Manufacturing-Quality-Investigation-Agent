## CI/CD

The project uses GitHub Actions to validate every push and pull request.

CI verifies:

- Python source compilation
- Ruff linting
- Security checks
- Investigation evaluation
- Docker production image build

Pipeline:

```text
Git Push / Pull Request
        ↓
Code Quality
        ↓
Security
        ↓
Evaluation
        ↓
Docker Build
        ↓
CI PASS