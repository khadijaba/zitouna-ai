# Frontend · Angular

**Owner:** Membre 4 · Angular 21 (standalone components, signals), SCSS.

```
src/app/
├── core/
│   ├── api/        models.ts (mirror of docs/api-contract.md), ParcelService, AiService
│   └── auth/       AuthService (JWT in localStorage), interceptor, guard
├── layout/         Shell: top bar + navigation
├── shared/         MockBadge, error helpers
└── features/
    ├── auth/       login, register
    ├── parcels/    list + detail (M2 irrigation, M3 yield, M6 tree count, harvest plan)
    ├── diagnosis/  M1 leaf photo
    ├── price/      M4 forecast + advice
    ├── assistant/  M5 chat
    └── history/    past predictions
```

## Run

```bash
npm install
npm start          # http://localhost:4200, /api is proxied to http://localhost:8080 (proxy.conf.json)
```

The backend must be running (see the root README). AI results show a **"données de démo"** badge while a module has no trained model.

## Test & build

```bash
npx ng test        # Vitest
npm run build
```

## Rules

- Components never call the AI services directly: always the backend through `AiService`.
- When the contract changes, update `core/api/models.ts` in the same PR.
- New page: `ng generate component features/<name>/<name>` and add a lazy route in `app.routes.ts`.
