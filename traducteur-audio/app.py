from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import routers.auth_router as auth_router
import routers.courses_router as courses_router
import routers.realtime_router as realtime_router
import routers.file_router as file_router
from core.config import settings
from routers.translations_router import router as translations_router


app = FastAPI()
app.include_router(translations_router)
# Monter le dossier public (situé à la racine) sur /static
app.mount("/static", StaticFiles(directory="../public"), name="static")

# Configuration des templates depuis public/html
templates = Jinja2Templates(directory="../public/html")

# Routes de pages avec des noms pour url_for
@app.get("/", name="index")
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login.html", name="login_page")
async def read_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register.html", name="register_page")
async def read_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/profile.html", name="profile_page")
async def read_profile(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request})

@app.get("/course.html", name="course_page")
async def read_course(request: Request):
    return templates.TemplateResponse("course.html", {"request": request})

@app.get("/app.html", name="app_page")
async def read_app(request: Request):
    return templates.TemplateResponse("app.html", {"request": request})

@app.get("/terms.html", name="terms_page")
async def read_terms(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})

@app.get("/policy.html", name="policy_page")
async def read_policy(request: Request):
    return templates.TemplateResponse("policy.html", {"request": request})

@app.get("/error.html", name="error_page")
async def read_error(request: Request):
    return templates.TemplateResponse("error.html", {"request": request})

# Inclusion des routeurs API
app.include_router(auth_router.router)
app.include_router(courses_router.router)
app.include_router(realtime_router.router)
app.include_router(file_router.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT) 