# Security policy

This dashboard is intended for confidential internal business information.

## Non-negotiable controls

- Keep the source repository private.
- Do not use public GitHub Pages.
- Protect the entire deployed hostname with company identity authentication and default-deny access.
- Require MFA for GitHub, Cloudflare, and the company identity provider.
- Store API credentials only in managed secrets; never in HTML, JSON, source files, screenshots, issues, or chat.
- Grant repository write access only to maintainers. Dashboard viewers do not need repository access.
- Review authorized users quarterly and remove access immediately when roles change.
- Preserve source attribution and market-data licensing requirements.
- Do not place customer names, contract prices, forecasts, personal data, credentials, or unpublished financial results in `dashboard.json` unless company security has explicitly approved the hosting environment.

## Incident response

If a credential or confidential value is committed:

1. Revoke or rotate the credential immediately.
2. Disable the affected deployment or access policy.
3. Notify the company security owner.
4. Remove the value from current files and repository history.
5. Review access and deployment logs.

Do not report sensitive incidents through a public GitHub issue.
