# app/main.py
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import logging
from typing import Optional, Dict, Any
import traceback

from .models import RepositoryUrl, AnalysisResult
from .github_client import GitHubClient
from .analyzer import ProjectAnalyzer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="GitHub Project Analyzer",
    description="A tool to analyze GitHub repositories and generate detailed project descriptions",
    version="0.1.0"
)

# Set up templates
templates = Jinja2Templates(directory="app/templates")

# Mount static files directory
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.error(f"Error mounting static files: {str(e)}. Static files may not be available.")

# Create GitHub client and project analyzer
github_token = os.getenv("GITHUB_TOKEN")
github_client = GitHubClient(token=github_token)
project_analyzer = ProjectAnalyzer(github_client=github_client)

# In-memory cache for analysis results
# In a production app, you'd use Redis or another caching solution
analysis_cache = {}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the homepage with the input form"""
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "title": "GitHub Project Analyzer"}
    )


@app.post("/analyze", response_class=HTMLResponse)
async def analyze_repository(request: Request, repo_url: str = Form(...)):
    """Analyze a GitHub repository and display results"""
    try:
        # Validate URL
        repo_url_model = RepositoryUrl(url=repo_url)
        url = repo_url_model.url
        
        # Check cache first
        if url in analysis_cache:
            logger.info(f"Using cached analysis for {url}")
            analysis_result = analysis_cache[url]
        else:
            # Perform analysis
            logger.info(f"Analyzing repository: {url}")
            analysis_result = project_analyzer.analyze_project(url)
            
            if "error" in analysis_result:
                return templates.TemplateResponse(
                    "index.html", 
                    {
                        "request": request, 
                        "title": "GitHub Project Analyzer", 
                        "error": analysis_result["error"]
                    }
                )

            # Cache the result
            analysis_cache[url] = analysis_result
            
        return templates.TemplateResponse(
            "results.html", 
            {
                "request": request, 
                "title": f"Analysis of {url}",
                "result": analysis_result,
                "repo_url": url
            }
        )
    except ValueError as e:
        logger.warning(f"Invalid repository URL: {str(e)}")
        return templates.TemplateResponse(
            "index.html", 
            {
                "request": request, 
                "title": "GitHub Project Analyzer", 
                "error": str(e)
            }
        )
    except Exception as e:
        logger.error(f"Error analyzing repository: {str(e)}")
        logger.error(traceback.format_exc())
        return templates.TemplateResponse(
            "index.html", 
            {
                "request": request, 
                "title": "GitHub Project Analyzer", 
                "error": "An error occurred while analyzing the repository. Please try again."
            }
        )


@app.get("/api/analyze/{owner}/{repo}", response_model=None)  # Removed strict response model for flexibility
async def api_analyze_repository(owner: str, repo: str):
    """API endpoint to analyze a GitHub repository"""
    try:
        url = f"https://github.com/{owner}/{repo}"
        
        # Check cache first
        if url in analysis_cache:
            return analysis_cache[url]
        
        # Perform analysis
        logger.info(f"API: Analyzing repository: {url}")
        analysis_result = project_analyzer.analyze_project(url)
        
        if "error" in analysis_result:
            raise HTTPException(status_code=400, detail=analysis_result["error"])
        
        # Cache the result
        analysis_cache[url] = analysis_result
        
        return analysis_result
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"API: Error analyzing repository: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "analyzer": "ready", "github_client": "connected" if github_client else "not connected"}


@app.get("/clear-cache")
async def clear_cache():
    """Admin endpoint to clear the analysis cache"""
    global analysis_cache
    cache_size = len(analysis_cache)
    analysis_cache = {}
    return {"status": "cache cleared", "items_removed": cache_size}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)