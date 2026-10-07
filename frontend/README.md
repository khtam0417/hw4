# Campus Customs website (frontend)

The React + Vite + TypeScript site for Campus Customs. See the [README in the repository folder](../README.md) to install, configure and run it together with the FastAPI backend.

Quick reference, from the repository folder:

```bash
npm --prefix frontend install    # once
npm --prefix frontend run dev    # http://localhost:5174, forwarding /api and /media to the backend on port 8000
npm --prefix frontend run lint   # oxlint
npm --prefix frontend run build  # type-check and build into frontend/dist
```

Set `BACKEND_PORT` when the backend runs on another port, for example `BACKEND_PORT=8001 npm --prefix frontend run dev`.
