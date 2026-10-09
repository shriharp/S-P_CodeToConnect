
# Security and Licensing

## Security Principles
- Treat all ingested source content as untrusted.
- Validate inputs and enforce size limits.
- Validate URLs and address SSRF risks.
- Never commit credentials or secrets.
- Pin dependencies where practical.
- Review model and dataset supply-chain risks.
- Use least-privilege container configurations.

## Security Tools
Prefer free/open-source tooling:
- Bandit: Python static analysis.
- pip-audit: Python dependencies.
- npm audit: frontend dependencies.
- Gitleaks: secret detection.
- Trivy: container scanning.

Investigate findings and document unresolved risks.

Passing scans does not prove that software is secure.

## Third-Party Inventory
Track:
- Runtime and development dependencies.
- Model weights.
- Datasets.
- External APIs.
- Images and assets.
- Reused source code.

For each item record:
- Name/version.
- Source.
- License or terms.
- Attribution obligations.
- Redistribution restrictions.

## Licensing Rules
- Free access does not imply open-source licensing.
- Public data is not automatically redistributable.
- Verify model and dataset terms before adoption.
- Do not include proprietary or confidential client data.
- Maintain a root project LICENSE.
- Keep third-party notices separate from the project license.

The organizers recommend MIT, but the final project license remains undecided.

## Documentation
Record:
- Scan commands and results.
- Vulnerabilities and remediation.
- Unresolved findings.
- Third-party inventory.
- Redistribution assumptions.
