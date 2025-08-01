# Researcher Brief — Hot Now + Study Next (v1.4.0)

Adds:
- 🔥 `/trends/hot` — cross-source trending topics (last 3 days).
- 📚 `/study/next` — durable topics to learn (21-day signals).
- Frontend: Arial, tile view, top HotNow + StudyNext, **Summarize** button per card.

## Run
```powershell
cd <unzipped-folder>
Copy-Item .env.example .env
# Edit .env (set OPENAI_API_KEY if you want LLM summaries; add Reddit creds if you have them)

docker compose up -d --build api
docker compose run --rm worker researcherbrief-worker --once   # ingest + topics
docker compose up -d web

start http://localhost:8000/health
start http://localhost:5173
```
If 5173 is busy, change the `web` service port mapping in `docker-compose.yml` to `"5174:80"` and open http://localhost:5174.

## Re-run ingestion on demand
```powershell
docker compose run --rm worker researcherbrief-worker --once
```

## Notes
- Summaries are **manual** by default (click Summarize on a card). To auto-run: set `SUMMARY_AUTO=true`.
- Daily spend cap: `SUMMARY_DAILY_CAP_USD` (default $1.00).
- Reddit is optional; without creds it is skipped cleanly.
