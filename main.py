from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from database import init_db, upsert_business, get_all_businesses
from scraper import scrape_businesses


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


class ScrapeRequest(BaseModel):
    lat: float
    lon: float
    radius_km: float


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.post("/scrape")
async def scrape(req: ScrapeRequest):
    if req.radius_km <= 0 or req.radius_km > 100:
        raise HTTPException(status_code=400, detail="Raio deve ser entre 1 e 100 km.")

    businesses = await scrape_businesses(req.lat, req.lon, req.radius_km)

    new_count = 0
    for b in businesses:
        existing = await get_all_businesses()
        existing_ids = {e["place_id"] for e in existing}
        if b["place_id"] not in existing_ids:
            new_count += 1
        await upsert_business(b)

    all_businesses = await get_all_businesses()
    return {"scraped": len(businesses), "new": new_count, "businesses": all_businesses}


@app.get("/businesses")
async def list_businesses():
    return await get_all_businesses()
