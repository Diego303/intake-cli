---
title: User Service REST API
author: Product Team
priority: high
version: "1.0"
---

# User Service REST API

## Overview

Build a RESTful user management service. The service handles user registration,
authentication, profile management, and account deletion. It will serve as the
central identity service for the platform.

## Functional Requirements

### Registration

When a new user submits a registration form with email, password, and display name,
the system shall create a new account, send a verification email, and return a
201 response with the user profile, so that users can onboard without friction.

- Email must be unique across the system
- Password must be at least 8 characters with one uppercase and one digit
- Display name must be 2-50 characters

### Authentication

When a registered user submits valid credentials, the system shall return a JWT
access token (15 min TTL) and a refresh token (7 day TTL), so that the user can
access protected endpoints.

When an access token expires, the system shall allow the user to obtain a new
access token using a valid refresh token, so that sessions persist without
re-entering credentials.

### Profile Management

- Users can view their own profile (GET /users/me)
- Users can update their display name and avatar (PATCH /users/me)
- Users can change their password (PUT /users/me/password)

### Account Deletion

When a user requests account deletion, the system shall soft-delete the account
(30 day retention), send a confirmation email, and revoke all active tokens,
so that users can recover their account if the deletion was accidental.

## Non-Functional Requirements

### Performance

- All API endpoints must respond within 200ms (p95)
- The service must handle 500 concurrent users
- Database queries must use indexes for all lookup fields

### Security

- Passwords must be hashed with bcrypt (cost factor 12)
- All endpoints must be served over HTTPS
- Rate limiting: 100 requests per minute per IP
- JWT tokens must be signed with RS256

### Reliability

- The service must have 99.9% uptime
- All mutations must be idempotent
- Failed email sends must be retried 3 times with exponential backoff
