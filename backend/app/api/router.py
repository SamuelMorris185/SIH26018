from fastapi import APIRouter
from app.api.routes import health, system, documents, digitization, records, validation, search, auth, audit, review, discrepancies, jobs, map

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(system.router)
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(digitization.router)
api_router.include_router(records.router)
api_router.include_router(discrepancies.router)
api_router.include_router(review.router)
api_router.include_router(validation.router)
api_router.include_router(search.router)
api_router.include_router(audit.router)
api_router.include_router(jobs.router)
api_router.include_router(map.router)


