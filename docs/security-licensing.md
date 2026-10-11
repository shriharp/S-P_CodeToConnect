
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

Current external sources:
- GDELT DOC 2.0: free public news search API; rate limits apply. Responses are
  retained only as source evidence and are not bundled as a dataset.
- StockTwits stream API: free public social stream used with its crowd labels;
  requests are throttled and source attribution is retained.
- Reddit public RSS (`r/stocks/search.rss`): keyless public RSS enrichment.
  RSS provides posts and timestamps, not authoritative sentiment. Use remains
  optional and must degrade visibly on 403, 429, or network failure.
- yfinance: open-source client for Yahoo Finance data. The application treats
  quotes as contextual market data and does not redistribute a price dataset.
- Curated demo corpus in `data/demo_news.jsonl`: project-authored replay
  fixtures with `provenance=replay`. This is the only dataset bundled for the
  demo path.

The Financial PhraseBank dataset was investigated for demo enrichment but is
licensed CC BY-NC-SA 3.0. It is not bundled or downloaded at runtime because
the non-commercial/share-alike terms need explicit compatibility review for a
public hackathon submission.

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
