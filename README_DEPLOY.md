# SAT-V&V v1.0.3 — original full application (with comparison chart fix)

This repository contains the **original entire** `/web/` frontend and the
complete `/satvv/` Python simulation engine, not the stripped-down static
showcase. Python code, 3D viewer, research navigation, all controls, all five
policies, and ML monitoring are preserved. Only `satvv/deployment_server.py`
is new: a bounded production HTTP adapter over the original PreviewHandler.

## Deploy on Render
1. Push the `satvv-live-backend` folder *contents* to a new GitHub repository,
   e.g. `saujanyadubale/satvv-live` (keep Dockerfile in the repository root).
2. In Render: New > Blueprint, connect the repository containing `render.yaml`.
   Review the service, pricing, region and create the web service.
   Blueprint uses Docker, `PORT=10000`, and starts the Python server.
3. When Render reports Live, open `https://<YOUR-SERVICE>.onrender.com/`.
   Test `/api/health`, configure a fault, run an experiment, and compare 5 methods.
4. Put that full `https://...onrender.com/` URL in the GitHub Pages project's
   `satvv/app-config.js` file. Push the Pages `satvv/` folder.
5. Load `https://saujanyadubale.github.io/satvv/`. It displays the full
   original live application in an iframe with a Fullscreen option.

## Limits and security
- `Content-Length` <=8192 bytes, bounded budget, severity, seed and duration.
- At most 3 overlapping simulation requests by default; 60 posts/min globally.
- Invalid requests get 400/413; overload gets 429. No CORS enabled.
- Iframe is limited to the portfolio origin by `frame-ancestors`.
- Keep the Render account and costs under review. Render instances differ in
  CPU/RAM; 5-way compare may require a larger instance in heavy traffic.
- A successful smoke test is *not* a production security audit or flight validation.
- Third-party Three.js asset CDN requires user network access.
- Do not open the original `python -m satvv serve` preview server to the internet.
- If you need production-grade multi-tenant scale, move computation to a queue with
  per-user quotas, deadline control, cancellation and metrics before promotion.

## Local preview of the public adapter
`python -m satvv.deployment_server` and open `http://localhost:10000/`.
Local original: `python -m satvv serve` and open `http://127.0.0.1:8765/`.

Original source licensing is **not declared** in this package. Decide on an
explicit LICENSE before making an open-source release.
