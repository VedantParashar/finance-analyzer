# Security policy

## Supported versions

Only the latest release and the live app at https://datadough.streamlit.app get fixes.

## Reporting a vulnerability

Please **don't open a public issue**. Use GitHub's private reporting instead: the **Security** tab of
this repository → **Report a vulnerability**. You should get an answer within a week.

## What's in scope

The app has no user accounts and stores no personal data. It reads public SEC filings and Yahoo Finance
prices, and keeps a local cache. Things worth reporting: a way to make the app fetch or link to
something it shouldn't (for example through the `?ticker=` and `?compare=` links or the feedback
setting), a leak of the hosted app's secrets (`SEC_USER_AGENT`), or a vulnerable dependency we use in a
vulnerable way.

A wrong number isn't a security issue: use "Report a wrong number" in the app or the
[issue list](https://github.com/VedantParashar/finance-analyzer/issues).
