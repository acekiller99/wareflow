from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, warehouses, products, inventory, suppliers, inbound, outbound, transfers, stock_counts, reports

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(warehouses.router)
app.include_router(products.router)
app.include_router(inventory.router)
app.include_router(suppliers.router)
app.include_router(inbound.router)
app.include_router(outbound.router)
app.include_router(transfers.router)
app.include_router(stock_counts.router)
app.include_router(reports.router)


@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}
