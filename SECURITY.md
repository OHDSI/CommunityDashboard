# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please email the maintainers directly with:

1. A description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if any)

We will acknowledge receipt within 48 hours and provide a timeline for a fix.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| latest  | Yes                |

## Security Considerations

### Environment Variables

This application requires several sensitive environment variables. Never commit `.env` files or API keys to the repository. See `.env.example` for the required configuration.

### Authentication

- JWT-based authentication with configurable token expiry
- Passwords are hashed using bcrypt
- Admin accounts are bootstrapped from environment variables on first startup
- Review and admin operations require authentication

### Data Access

- Search functionality is publicly accessible (read-only)
- Content review and approval require reviewer or admin roles
- User management requires admin role
