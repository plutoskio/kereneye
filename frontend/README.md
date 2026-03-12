# KerenEye Frontend

React + Vite single-page app for the KerenEye portfolio dashboard and stock research views.

## Routes

- `/` portfolio dashboard
- `/stock/:ticker` stock detail with executive dossier and news analysis
- `/transactions` transaction history

## Development

```bash
npm install
npm run dev
```

The app expects the FastAPI backend to be running on `http://localhost:8000`.

Set `VITE_API_BASE_URL` to override the default backend URL.

## Build

```bash
npm run build
npm run preview
```
