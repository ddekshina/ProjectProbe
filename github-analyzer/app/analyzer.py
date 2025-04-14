import re
import os
from typing import Dict, Any, List, Optional
import requests
from app.github_client import GitHubClient

class ProjectAnalyzer:
    def __init__(self, github_client: Optional[GitHubClient] = None):
        """Initialize the analyzer with an optional GitHubClient"""
        self.github_client = github_client or GitHubClient()
        self.groq_api_key = os.getenv("GROQ_API_KEY")
    
    def analyze_project(self, repo_url: str) -> Dict[str, Any]:
        """Main function to analyze a GitHub project"""
        # Get basic repo information
        repo_info = self.github_client.get_repo_info(repo_url)
        if "error" in repo_info:
            return {"error": repo_info["error"]}
        
        # Get README content
        readme = self.github_client.get_readme(repo_url)
        
        # Get file structure
        file_structure = self.github_client.get_file_structure(repo_url)
        
        # Get language distribution
        languages = self.github_client.get_languages(repo_url)
        
        # Get sample code
        sample_code = self.github_client.get_sample_code(repo_url)
        
        # Get contributors
        contributors = self.github_client.get_contributors(repo_url)
        
        # Analyze collected information
        project_description = self._generate_description(
            repo_info, 
            readme, 
            file_structure, 
            languages, 
            sample_code
        )
        
        # Prepare the result
        return {
            "repo_info": repo_info,
            "readme": readme,
            "file_structure": file_structure,
            "languages": languages,
            "contributors": contributors,
            "description": project_description,
            "sample_code": sample_code
        }
    
    def _generate_description(
        self, 
        repo_info: Dict[str, Any], 
        readme: str, 
        file_structure: Dict[str, Any], 
        languages: Dict[str, int], 
        sample_code: Dict[str, str]
    ) -> Dict[str, Any]:
        """Generate a comprehensive description of the project"""
        # Start with basic analysis
        description = {
            "summary": self._generate_summary(repo_info, readme),
            "architecture": self._analyze_architecture(file_structure, languages),
            "main_features": self._extract_features(readme, sample_code),
            "technologies": self._identify_technologies(languages, file_structure, readme, sample_code),
            "setup_instructions": self._extract_setup_instructions(readme),
            "code_quality": self._assess_code_quality(sample_code)
        }
        
        # Try to enhance with AI if API key is available
        if self.groq_api_key:
            ai_description = self._generate_ai_description(
                repo_info, readme, file_structure, languages, sample_code
            )
            if ai_description:
                description["ai_enhanced"] = ai_description
        
        return description
    
    def _generate_summary(self, repo_info: Dict[str, Any], readme: str) -> str:
        """Generate a summary of the project"""
        summary = repo_info.get("description", "No description provided.")
        
        # Extract first paragraph from README if description is missing
        if summary == "No description provided." and readme:
            # Try to find the first paragraph after the title
            paragraphs = re.split(r'\n\s*\n', readme)
            for p in paragraphs:
                # Skip headings or badges
                if not p.strip().startswith('#') and not '![' in p and len(p.strip()) > 30:
                    summary = p.strip()
                    break
        
        # Add some stats
        stats = []
        if repo_info.get("stars"):
            stats.append(f"{repo_info['stars']} stars")
        if repo_info.get("forks"):
            stats.append(f"{repo_info['forks']} forks")
            
        summary = summary or ""
        if stats:
            summary += f" This project has {', '.join(stats)}."
        
        return summary
    
    def _analyze_architecture(self, file_structure: Dict[str, Any], languages: Dict[str, int]) -> str:
        """Analyze the architecture of the project"""
        architecture = "Project structure analysis:\n\n"
        
        # Identify common patterns in the structure
        if "src" in file_structure or "app" in file_structure:
            architecture += "- This project follows a structured development approach with separated source code.\n"
        
        if "tests" in file_structure or "test" in file_structure:
            architecture += "- The project includes tests, suggesting a focus on code quality and reliability.\n"
        
        if "docs" in file_structure:
            architecture += "- Documentation is separated into its own directory, indicating good project organization.\n"
        
        if "package.json" in file_structure:
            architecture += "- This is a Node.js project using npm or yarn for package management.\n"
        
        if "requirements.txt" in file_structure or "Pipfile" in file_structure:
            architecture += "- This is a Python project with dependency management.\n"
        
        if "docker-compose.yml" in file_structure or "Dockerfile" in file_structure:
            architecture += "- The project uses Docker for containerization.\n"
        
        if "public" in file_structure and "src" in file_structure:
            architecture += "- This appears to be a frontend application with separated public assets.\n"
        
        # Language distribution
        if languages:
            total = sum(languages.values())
            architecture += "\nLanguage distribution:\n"
            for lang, bytes_count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
                percentage = (bytes_count / total) * 100
                architecture += f"- {lang}: {percentage:.1f}%\n"
        
        return architecture
    
    def _extract_features(self, readme: str, sample_code: Dict[str, str]) -> List[str]:
        """Extract main features from README and code"""
        features = []
        
        # Look for features in README
        feature_patterns = [
            r'(?:^|\n)#+\s*Features?\s*\n+((?:.+\n)+?)',
            r'(?:^|\n)#+\s*What.*?(?:do|does)\s*\n+((?:.+\n)+?)'
        ]
        
        for pattern in feature_patterns:
            matches = re.search(pattern, readme, re.IGNORECASE)
            if matches:
                # Extract features from bullet points
                feature_text = matches.group(1)
                bullet_features = re.findall(r'[-*]\s+(.+)', feature_text)
                if bullet_features:
                    features.extend(bullet_features)
        
        # If no features found in specific sections, try to guess from README
        if not features:
            # Look for bullet points that might describe features
            bullet_features = re.findall(r'[-*]\s+([A-Z].*?\.)', readme)
            features.extend(bullet_features[:5])  # Limit to first 5 potential features
        
        # Add generic features if nothing specific found
        if not features:
            main_lang = self._identify_main_language(sample_code)
            if main_lang == "Python":
                features = ["Python-based application", "Modular structure", "Command-line interface"]
            elif main_lang == "JavaScript":
                features = ["JavaScript-based application", "Web interface", "Modern JS architecture"]
            else:
                features = ["Software application", "Structured codebase", "Developer-friendly"]
        
        return features[:7]  # Limit to 7 most important features
    
    def _identify_technologies(
        self, 
        languages: Dict[str, int], 
        file_structure: Dict[str, Any], 
        readme: str, 
        sample_code: Dict[str, str]
    ) -> Dict[str, List[str]]:
        """Identify technologies used in the project"""
        technologies = {
            "languages": [],
            "frameworks": [],
            "libraries": [],
            "tools": []
        }
        
        # Add languages
        if languages:
            technologies["languages"] = list(languages.keys())
        
        # Check for common frameworks and libraries based on files
        files_str = str(file_structure)
        
        # Python frameworks
        if "Django" in files_str or "django" in files_str:
            technologies["frameworks"].append("Django")
        if "Flask" in files_str or "flask" in files_str:
            technologies["frameworks"].append("Flask")
        if "FastAPI" in files_str or "fastapi" in files_str:
            technologies["frameworks"].append("FastAPI")
        
        # JavaScript frameworks
        if "react" in files_str:
            technologies["frameworks"].append("React")
        if "angular" in files_str:
            technologies["frameworks"].append("Angular")
        if "vue" in files_str:
            technologies["frameworks"].append("Vue.js")
        if "next.js" in files_str or "next" in files_str:
            technologies["frameworks"].append("Next.js")
        
        # Database technologies
        if "mongo" in files_str.lower():
            technologies["libraries"].append("MongoDB")
        if "postgres" in files_str.lower():
            technologies["libraries"].append("PostgreSQL")
        if "mysql" in files_str.lower():
            technologies["libraries"].append("MySQL")
        if "sqlite" in files_str.lower():
            technologies["libraries"].append("SQLite")
        
        # Build tools
        if "webpack" in files_str.lower():
            technologies["tools"].append("Webpack")
        if "vite" in files_str.lower():
            technologies["tools"].append("Vite")
        if "gulp" in files_str.lower():
            technologies["tools"].append("Gulp")
        
        # Testing frameworks
        if "jest" in files_str.lower():
            technologies["tools"].append("Jest")
        if "pytest" in files_str.lower():
            technologies["tools"].append("pytest")
        if "mocha" in files_str.lower():
            technologies["tools"].append("Mocha")
        
        # Look for imports in Python code
        for _, code in sample_code.items():
            if code.startswith("Could not retrieve"):
                continue
                
            if ".py" in code or "import " in code:
                python_imports = re.findall(r'import (\w+)|from (\w+)', code)
                for match in python_imports:
                    imp = match[0] or match[1]
                    if imp and imp not in ["os", "sys", "re", "json", "time", "math", "random", "typing"]:
                        if imp not in technologies["libraries"]:
                            technologies["libraries"].append(imp)
            
            # Look for npm packages
            if "require(" in code or "import" in code and "from" in code:
                js_imports = re.findall(r'require\([\'"]([^\'"]+)[\'"]\)|from\s+[\'"]([^\'"]+)[\'"]', code)
                for match in js_imports:
                    imp = match[0] or match[1]
                    if imp and not imp.startswith(".") and imp not in technologies["libraries"]:
                        # Clean package names (remove paths)
                        pkg = imp.split("/")[0]
                        if pkg not in technologies["libraries"]:
                            technologies["libraries"].append(pkg)
        
        # Limit results to avoid overwhelming information
        for category in technologies:
            technologies[category] = technologies[category][:10]
        
        return technologies
    
    def _extract_setup_instructions(self, readme: str) -> str:
        """Extract setup instructions from README"""
        setup_sections = [
            r'(?:^|\n)#+\s*(?:Installation|Setup|Getting Started)\s*\n+((?:.+\n)+?)\n(?:#+\s|$)',
            r'(?:^|\n)#+\s*How to [Ii]nstall\s*\n+((?:.+\n)+?)\n(?:#+\s|$)',
            r'(?:^|\n)#+\s*[Uu]sage\s*\n+((?:.+\n)+?)\n(?:#+\s|$)'
        ]
        
        for pattern in setup_sections:
            match = re.search(pattern, readme)
            if match:
                return match.group(1).strip()
        
        return "No setup instructions found in the README."
    
    def _assess_code_quality(self, sample_code: Dict[str, str]) -> str:
        """Perform a basic code quality assessment"""
        if not sample_code or "error" in sample_code:
            return "Could not assess code quality due to limited access to code files."
        
        quality_assessment = "Code quality assessment:\n\n"
        
        # Look for code smells and good practices
        total_length = 0
        comment_lines = 0
        long_lines = 0
        complex_functions = 0
        
        for file_path, code in sample_code.items():
            if code.startswith("Could not retrieve"):
                continue
                
            lines = code.split('\n')
            total_length += len(lines)
            
            # Count comment lines
            for line in lines:
                line = line.strip()
                if line.startswith('#') or line.startswith('//') or line.startswith('/*'):
                    comment_lines += 1
            
            # Count long lines
            long_lines += sum(1 for line in lines if len(line) > 100)
            
            # Look for potentially complex functions
            if '.py' in file_path:
                # Look for Python functions with many lines
                python_funcs = re.findall(r'def\s+\w+\([^)]*\):\s*\n((?:\s+.+\n)+)', code)
                for func in python_funcs:
                    if func.count('\n') > 30:
                        complex_functions += 1
            elif '.js' in file_path:
                # Look for JS functions with many lines
                js_funcs = re.findall(r'function\s+\w+\([^)]*\)\s*{((?:.+\n)+?)}', code)
                for func in js_funcs:
                    if func.count('\n') > 30:
                        complex_functions += 1
        
        # Calculate metrics
        if total_length > 0:
            comment_ratio = (comment_lines / total_length) * 100
            long_lines_ratio = (long_lines / total_length) * 100
            
            quality_assessment += f"- Documentation: {'Good' if comment_ratio > 15 else 'Average' if comment_ratio > 5 else 'Minimal'} ({comment_ratio:.1f}% comment lines)\n"
            quality_assessment += f"- Code readability: {'Good' if long_lines_ratio < 5 else 'Average' if long_lines_ratio < 15 else 'Could be improved'} ({long_lines_ratio:.1f}% long lines)\n"
            quality_assessment += f"- Complexity: {'Low' if complex_functions == 0 else 'Medium' if complex_functions < 3 else 'High'} ({complex_functions} potentially complex functions)\n"
        else:
            quality_assessment += "- Insufficient code available for quality assessment\n"
        
        # Look for good practices
        good_practices = []
        if "test" in str(sample_code).lower():
            good_practices.append("Evidence of testing")
        
        if "docstring" in str(sample_code).lower() or '"""' in str(sample_code):
            good_practices.append("Docstrings in code")
            
        if "type" in str(sample_code).lower() and (":" in str(sample_code) or "TypeScript" in str(sample_code)):
            good_practices.append("Type annotations")
        
        if good_practices:
            quality_assessment += "- Good practices observed: " + ", ".join(good_practices) + "\n"
        
        return quality_assessment
    
    def _identify_main_language(self, sample_code: Dict[str, str]) -> str:
        """Identify the main programming language based on sample code"""
        extensions = []
        for file_path in sample_code.keys():
            if "." in file_path:
                ext = file_path.split(".")[-1].lower()
                extensions.append(ext)
        
        if not extensions:
            return "Unknown"
        
        # Count occurrences of each extension
        ext_count = {}
        for ext in extensions:
            ext_count[ext] = ext_count.get(ext, 0) + 1
        
        # Map extension to language name
        main_ext = max(ext_count, key=ext_count.get)
        
        lang_map = {
            "py": "Python",
            "js": "JavaScript",
            "ts": "TypeScript",
            "java": "Java",
            "c": "C",
            "cpp": "C++",
            "cs": "C#",
            "go": "Go",
            "rs": "Rust",
            "rb": "Ruby",
            "php": "PHP",
            "swift": "Swift",
            "kt": "Kotlin"
        }
        
        return lang_map.get(main_ext, main_ext.capitalize())
    
    def _generate_ai_description(
        self, 
        repo_info: Dict[str, Any], 
        readme: str, 
        file_structure: Dict[str, Any], 
        languages: Dict[str, int], 
        sample_code: Dict[str, str]
    ) -> Optional[Dict[str, str]]:
        """Use Groq API to generate an enhanced description"""
        if not self.groq_api_key:
            return None
        
        try:
            # Prepare data for AI analysis
            context = {
                "name": repo_info.get("name", ""),
                "description": repo_info.get("description", ""),
                "readme_excerpt": readme[:5000] if readme else "",
                "languages": str(languages),
                "file_structure": str(file_structure)[:1000],
                "sample_code": str(sample_code)[:3000] if sample_code else ""
            }
            
            prompt = f"""
            Analyze this GitHub project and provide a comprehensive description:
            
            Project name: {context['name']}
            Project description: {context['description']}
            
            README excerpt:
            {context['readme_excerpt']}
            
            Languages used:
            {context['languages']}
            
            File structure:
            {context['file_structure']}
            
            Sample code:
            {context['sample_code']}
            
            Please provide:
            1. A concise summary (2-3 sentences)
            2. Main features (5 bullet points)
            3. Architecture description (2-3 paragraphs)
            4. Use cases (who would benefit from this project)
            5. Technical assessment (strengths and potential improvements)
            """
            
            # Make API call to Groq
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama3-8b-8192",  # You can use different models as available
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_content = result["choices"][0]["message"]["content"]
                
                # Parse the AI response
                sections = re.split(r'\n\d+\.\s+', ai_content)
                
                if len(sections) >= 6:  # First element is empty due to the split
                    return {
                        "summary": sections[1].strip(),
                        "features": sections[2].strip(),
                        "architecture": sections[3].strip(),
                        "use_cases": sections[4].strip(),
                        "technical_assessment": sections[5].strip()
                    }
            
            return None
        except Exception as e:
            print(f"Error generating AI description: {str(e)}")
            return None