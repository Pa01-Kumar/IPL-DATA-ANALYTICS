# IPL Intelligence Web

Next.js frontend for the IPL Intelligence platform. It consumes the Python FastAPI service at `http://localhost:8000`.

## Run

From the repository root, start the API:

```bash
python -m pip install -r api/requirements.txt
uvicorn api.main:app --reload --port 8000
```

In a second terminal:

```bash
cd web
npm install
npm run dev
```

Open http://localhost:3000. Copy `.env.example` to `.env.local` if the API is hosted elsewhere.

The existing Streamlit app remains available during the migration with `streamlit run app/dashboard.py`.
