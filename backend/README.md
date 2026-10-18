# Backend · Spring Boot

**Owner:** Membre 2 · Spring Boot 4, Java 21, PostgreSQL (JPA + Flyway), Spring Security (JWT).

The core of the app: authentication, users, parcels, prediction history, and orchestration of the six AI services.

```
src/main/java/tn/zitouna/
├── config/          SecurityConfig (JWT), AiProperties (service URLs)
├── auth/            register / login, issues the JWT
├── user/            User entity, GET /api/users/me
├── parcel/          olive groves CRUD (owner-scoped)
├── history/         every AI call is saved here
├── common/          errors (ProblemDetail), pagination
├── status/          GET /api/status: backend, database and the six AI services (public)
├── admin/           back-office API /api/admin/** (ADMIN role) + first admin account (AdminBootstrap)
└── ai/
    ├── AiServiceClient     base HTTP client: timeouts, 400/503 mapping
    ├── disease/            M1 client + controller
    ├── irrigation/         M2
    ├── cropyield/          M3
    ├── price/              M4
    ├── assistant/          M5 + ChatService (routes intents to M2/M3/M4)
    ├── trees/              M6
    └── orchestration/      HarvestPlanService: M6 -> M3 -> M4
```

## Run

```bash
docker compose up postgres            # from the repo root (+ the AI services you need)
./mvnw spring-boot:run                # Windows: mvnw.cmd spring-boot:run
```

**Home page: http://localhost:8080** (`src/main/resources/static/index.html`): live state of the backend, the
database and the six AI services (online, real model or demo mode), every API route, how to call it, link to the app.
It reads the public `GET /api/status` and refreshes every 15 s.

Call the API: `POST /api/auth/register` or `/api/auth/login` returns a JWT, then send it as
`Authorization: Bearer <token>` (examples with PowerShell and curl on the home page).

In IntelliJ: open the `backend/` folder, select JDK 21, run `ZitounaBackendApplication` (stop the Docker backend
first: `docker compose stop backend`, port 8080).

## Admin back-office

The back-office is in the app: **http://localhost:4200/admin** (menu « ⚙ Admin », shown to admins only). It calls
`/api/admin/**`, where every endpoint requires the `ADMIN` role (403 « Réservé aux administrateurs » otherwise).

| Endpoint | What |
|---|---|
| `GET /api/admin/stats` | totals (users, parcels, trees, hectares, predictions), predictions per day (30 days), per module, parcels per governorate, live state of the AI services |
| `GET /api/admin/users?q=&page=` | every account, search on name / email, number of parcels and predictions |
| `DELETE /api/admin/users/{id}` | delete a farmer account with its parcels and history (the admin: 409) |
| `GET /api/admin/parcels?q=&page=` · `DELETE /api/admin/parcels/{id}` | every parcel with its owner |
| `GET /api/admin/predictions?type=&page=` | every AI call (request + response), filter by module |

**One admin, two kinds of accounts.** The platform has exactly **one** administrator, defined in `.env`
(`ADMIN_EMAIL`, `ADMIN_PASSWORD` ≥ 8 characters) and applied at every backend start-up (`AdminBootstrap`): the
account is created (or promoted), its password is the one of `.env`, and any other ADMIN account becomes FARMER.
Roles cannot be changed from the app, and everyone who registers is a FARMER. After `docker compose up -d backend`:

- log in with the admin email → the app opens the back-office (`/admin`), menu « ⚙ Administration » only;
- log in with any other account → the farmer app (parcels, diagnosis, irrigation, price, assistant, history).

Configuration is in `src/main/resources/application.properties`, overridable with env vars (`DB_URL`, `JWT_SECRET`, `AI_M1_URL`…).

## Test

```bash
./mvnw verify
```

Tests use an in-memory H2 database (`application-test.properties`), no PostgreSQL needed.

## Rules

- **Database changes = new Flyway migration** `src/main/resources/db/migration/V2__add_xxx.sql`. Never edit a migration that is already merged; Hibernate only validates the schema.
- Always fetch parcels with `ParcelService.getOwned(userId, parcelId)` so a user can never see another user's data.
- A new AI field: update the `…Result` record **and** [docs/api-contract.md](../docs/api-contract.md).
