from typing import Dict, List, Optional, Any
from pydantic import BaseModel, HttpUrl, validator, Field


class RepositoryUrl(BaseModel):
    """Model for repository URL input"""
    url: str = Field(..., description="GitHub repository URL")
    
    @validator('url')
    def validate_github_url(cls, v):
        """Validate that the URL is a GitHub repository URL"""
        v = v.strip()
        if not v.startswith(('https://github.com/', 'http://github.com/')):
            raise ValueError('URL must be a GitHub repository URL')
        
        # Normalize URL
        if v.endswith('/'):
            v = v[:-1]
        
        # Ensure there are at least 3 parts (https://github.com/owner/repo)
        parts = v.split('/')
        if len(parts) < 5:
            raise ValueError('URL must be a valid GitHub repository URL (https://github.com/owner/repo)')
        
        return v


class RepoInfo(BaseModel):
    """Model for repository basic information"""
    name: str
    full_name: str
    description: Optional[str] = None
    stars: int
    forks: int
    watchers: int
    language: Optional[str] = None
    created_at: str
    updated_at: str
    license: Optional[str] = None
    topics: List[str] = []
    owner: Dict[str, Any]


class ProjectDescription(BaseModel):
    """Model for project description"""
    summary: str
    architecture: str
    main_features: List[str]
    technologies: Dict[str, List[str]]
    setup_instructions: str
    code_quality: str
    ai_enhanced: Optional[Dict[str, str]] = None


class Contributor(BaseModel):
    """Model for repository contributor"""
    login: str
    contributions: int
    avatar_url: str
    html_url: str


class AnalysisResult(BaseModel):
    """Model for the complete analysis result"""
    repo_info: RepoInfo
    readme: str
    file_structure: Dict[str, Any]
    languages: Dict[str, int]
    contributors: List[Contributor]
    description: ProjectDescription
    sample_code: Dict[str, str]