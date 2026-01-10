List of technology that should be included in lockdev-saas-starter:

Principles:
- hippa compliant
- simple
- performant
- compatibility with AI

- infra
  - docker compose
  - GitHub Actions workflows
  - aptible (hosting)
    - app.domain.com (UI)
    - api.domain.com (API)
  - opentofu (IaC)
    - aptible
    - aws connect (IVR)
    - aws ses
    - Checkov (Policy as Code)
  - SOPS (versioned secrets)
    - Age (encrypt secrets via local keys.txt)
- structure
  - monorepo
    - make
- quality
  - prettier (format)
  - biome (lint)
  - pre-commit (git hooks)
  - typecheck
  - playwright (e2e)
- front end (static)
  - typescript
  - vite + react
  - pnpm (package management)
    - openapi-typescript (types from swagger docs)
  - tanstack (query, router, form)
  - zod (validation)
  - shadcn
  - vitest (unit)
  - axios (whitelist domains)
  - Google Cloud Identity Platform (client)
- back end (container)
  - python
    - uv (dependency management)
    - presidio (masking in logs, spans, traces)
    - pydantic2 (validation)
    - pydantic-settings (secret import)
    - Structlog (logging)
    - SlowAPI (rate limiting)
    - Server-Sent Events (SSE)
    - google-cloud-aiplatform
    - textract
    - LLM (Google Gemini)
  - fastapi
    - SQLAlchemy (orm)
      - Alembic (migrations)
    - Google Cloud Identity Platform (admin)
    - PostgreSQL-Audit (audits)
    - Audit Middleware (Read Access Logging for Staff)
    - httpx (whitelist domains)
- background worker (container)
  - ARQ
- database
  - postgres
  - redis
- storage
  - AWS S3

- 3rd party integrations
  - email (aws ses)
  - sms (aws end user messaging)
  - voice (aws connect)
  - payments (stripe)

Should consider things like:
- security
  - helmet (headers)
- compliance
  - audits by default (postgres trigger)
- devex
  - swagger docs
  - logging (cloudwatch)
  - observability (sentry + cloudwatch)
  - MFA (Internal Staff)
- data integrity
  - ULID primary keys (Universally Unique Lexicographically Sortable Identifier)
- legal
  - consent & ToS tracking (versioned)

---

## Data Model Architecture

### User Actors & Personas

**Clinical & Operational Staff:**
- Provider: Licensed clinician (MD, DO, NP, PA) with NPI/DEA identifiers. Can work across multiple Organizations.
- Clinical Staff: Support personnel (Nurses, Medical Assistants) assisting Providers.
- Administrative Staff: Front-desk/billing with scheduling and demographics access, restricted clinical notes.
- Organization Admin: Manages settings and user list for a specific Tenant (Organization).

**Patient & Family:**
- Self-Managed Patient: Competent adult receiving care with direct login credentials.
- Dependent Patient: Minor or incapacitated adult. **No login** - accessed via Proxy only.
- Patient Proxy: Legal guardian, parent, or power of attorney managing one or more Dependent Patients.

**System & Oversight:**
- Super Admin: Platform owner with full access to all tenants.
- Auditor/Compliance Officer: Read-only access to Audit Logs; restricted PHI access.
- Service Account (Bot): Non-human users (e.g., "Billing System Integration") for API actions.

### Core Entities

| Entity | Description | Key Attributes |
| --- | --- | --- |
| **Organization** | The tenant (Clinic/Hospital) | `id`, `name`, `tax_id`, `timezone`, `settings_json`, `deleted_at`, `stripe_customer_id`, `subscription_status` |
| **User** | The authentication record | `id`, `email`, `password_hash`, `mfa_enabled`, `timezone` (optional override) |
| **AuditLog** | Immutable record of actions | `actor_id`, `target_resource`, `action_type`, `ip_address`, `timestamp` |

### Role Entities

| Entity | Description | Key Attributes |
| --- | --- | --- |
| **Provider** | Licensed clinician profile | `npi_number`, `dea_number`, `state_licenses` (Array) |
| **Staff** | Non-provider employee | `employee_id`, `job_title` (e.g., Nurse, Biller) |
| **Patient** | The receiver of care | `mrn`, `dob`, `legal_sex`, `stripe_customer_id`, `subscription_status` |
| **Proxy** | The manager of care | `relationship_type` (Parent, Guardian) |

### Association Tables

- **Organization_Member**: Links `User` to `Organization` with a specific role (Provider, Staff).
- **Patient_Proxy_Assignment**: Links `Proxy` to `Patient` with `permissions_mask` (scope) and `relationship_proof` (document ID for POA).
- **Care_Team**: Links `Provider` to `Patient` within an `Organization`.

### Contact & Demographics

- **Contact_Method**: `type` (Mobile, Home, Email), `value`, `is_primary`, `is_safe_for_voicemail` (CRITICAL for patient safety)

### Functional Requirements

- **FR-01 User/Profile Separation**: Decouple `User` (login) from `Role` (Patient, Provider). Single email can hold multiple roles.
- **FR-02 Multi-Tenancy**: Users can belong to 0-Many Organizations with strict data segregation.
- **FR-03 Proxy Management**: Many-to-Many relationships between Proxies and Patients.
- **FR-04 Granular Consent**: Proxy permissions support scopes: `can_view_clinical`, `can_view_billing`, `can_schedule`.
- **FR-05 Safe Contact Protocol**: Distinguish standard vs "safe" contact to protect patient privacy.
- **FR-06 Subscriptions**: Dual-sided subscription model:
    - **Organization**: Pays to retain active platform status.
    - **Patient**: Pays a per-patient subscription (managed by Patient or Proxy) for access.
- **FR-07 Timezone Support**: All user-facing date/times displayed in configured timezone.
    - **Organization**: Stores default timezone (IANA format, e.g., "America/New_York").
    - **User**: Optional timezone override (null = use organization default).
    - **Storage**: All datetimes stored as UTC with timezone awareness.

### Assumptions

1. **US-Centric**: NPI and DEA identifiers are specific to US healthcare.
2. **Email as Identity**: Email is the unique identifier for `User` accounts.
3. **Soft Deletes**: No clinical data is hard deleted; only soft deleted (`deleted_at` timestamp).
