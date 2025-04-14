import os
import base64
from typing import Dict, List, Optional, Any
import requests
from github import Github
from dotenv import load_dotenv

load_dotenv()

class GitHubClient:
    def __init__(self, token: Optional[str] = None):
        """Initialize GitHub client with optional token for increased rate limits"""
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.github = Github(self.token) if self.token else Github()
        self.headers = {"Authorization": f"token {self.token}"} if self.token else {}
    
    def get_repo_info(self, repo_url: str) -> Dict[str, Any]:
        """Get basic information about a repository"""
        # Extract owner and repo name from URL
        parts = repo_url.rstrip('/').split('/')
        owner = parts[-2]
        repo_name = parts[-1]
        
        try:
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            
            return {
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "watchers": repo.watchers_count,
                "language": repo.language,
                "created_at": repo.created_at.isoformat(),
                "updated_at": repo.updated_at.isoformat(),
                "license": repo.license.name if repo.license else None,
                "topics": repo.get_topics(),
                "owner": {
                    "login": repo.owner.login,
                    "avatar_url": repo.owner.avatar_url,
                    "html_url": repo.owner.html_url
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_readme(self, repo_url: str) -> str:
        """Get the README content from a repository"""
        parts = repo_url.rstrip('/').split('/')
        owner = parts[-2]
        repo_name = parts[-1]
        
        try:
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            readme = repo.get_readme()
            content = base64.b64decode(readme.content).decode('utf-8')
            return content
        except Exception:
            return "No README found"
    
    def get_file_structure(self, repo_url: str, depth: int = 2) -> Dict[str, Any]:
        """Get the file structure of a repository up to specified depth"""
        parts = repo_url.rstrip('/').split('/')
        owner = parts[-2]
        repo_name = parts[-1]
        
        try:
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            contents = repo.get_contents("")
            
            structure = {}
            self._process_contents(contents, structure, repo, current_depth=0, max_depth=depth)
            return structure
        except Exception as e:
            return {"error": str(e)}
    
    def _process_contents(self, contents, structure, repo, current_path="", current_depth=0, max_depth=2):
        """Recursively processes repository contents"""
        if current_depth > max_depth:
            return
        
        for content in contents:
            if content.type == "dir":
                if current_depth < max_depth:
                    structure[content.name] = {}
                    new_contents = repo.get_contents(content.path)
                    self._process_contents(
                        new_contents, 
                        structure[content.name], 
                        repo, 
                        current_path=content.path,
                        current_depth=current_depth + 1,
                        max_depth=max_depth
                    )
            else:
                if content.name.endswith(('.py', '.js', '.ts', '.html', '.css', '.java', '.go', '.rs', '.cpp', '.c', '.md')):
                    structure[content.name] = content.path
    
    def get_languages(self, repo_url: str) -> Dict[str, int]:
        """Get the languages used in the repository with line counts"""
        parts = repo_url.rstrip('/').split('/')
        owner = parts[-2]
        repo_name = parts[-1]
        
        try:
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            return repo.get_languages()
        except Exception as e:
            return {"error": str(e)}
    
    def get_contributors(self, repo_url: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top contributors to the repository"""
        parts = repo_url.rstrip('/').split('/')
        owner = parts[-2]
        repo_name = parts[-1]
        
        try:
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            contributors = repo.get_contributors()
            
            result = []
            count = 0
            for contributor in contributors:
                if count >= limit:
                    break
                result.append({
                    "login": contributor.login,
                    "contributions": contributor.contributions,
                    "avatar_url": contributor.avatar_url,
                    "html_url": contributor.html_url
                })
                count += 1
            return result
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_commit_activity(self, repo_url: str) -> List[Dict[str, Any]]:
        """Get commit activity for the repository"""
        parts = repo_url.rstrip('/').split('/')
        owner = parts[-2]
        repo_name = parts[-1]
        
        try:
            url = f"https://api.github.com/repos/{owner}/{repo_name}/stats/commit_activity"
            response = requests.get(url, headers=self.headers)
            return response.json()
        except Exception as e:
            return [{"error": str(e)}]

    def get_sample_code(self, repo_url: str, max_files: int = 3) -> Dict[str, str]:
        """Get sample code from the repository (a few important files)"""
        parts = repo_url.rstrip('/').split('/')
        owner = parts[-2]
        repo_name = parts[-1]
        
        try:
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            contents = repo.get_contents("")
            
            # Files we're interested in
            main_files = []
            
            # First look for key files based on common patterns
            for pattern in ["main.py", "app.py", "index.js", "server.js", "main.js", "App.js", "index.html"]:
                for content in contents:
                    if content.name == pattern and content.type == "file":
                        main_files.append(content)
                        if len(main_files) >= max_files:
                            break
                if len(main_files) >= max_files:
                    break
            
            # If we didn't find enough key files, add some based on extensions
            if len(main_files) < max_files:
                for content in contents:
                    if content.type == "file" and content.name.endswith(('.py', '.js', '.html', '.css', '.java')):
                        if content not in main_files:
                            main_files.append(content)
                            if len(main_files) >= max_files:
                                break
            
            # Get the file contents
            result = {}
            for file in main_files:
                try:
                    file_content = repo.get_contents(file.path)
                    content = base64.b64decode(file_content.content).decode('utf-8')
                    result[file.path] = content
                except Exception:
                    result[file.path] = "Could not retrieve file content"
            
            return result
        except Exception as e:
            return {"error": str(e)}