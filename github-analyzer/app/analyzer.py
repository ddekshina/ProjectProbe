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
        try:
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
            
            # Get sample code (keep this for backward compatibility)
            sample_code = self.github_client.get_sample_code(repo_url)
            
            # Get full codebase (with size limits to prevent memory issues)
            full_codebase = self.github_client.get_full_codebase(repo_url)
            if not full_codebase:
                full_codebase = {}  # Ensure we have at least an empty dict
            
            # Get contributors
            contributors = self.github_client.get_contributors(repo_url)
            
            # Analyze collected information
            project_description = self._generate_description(
                repo_info, 
                readme, 
                file_structure, 
                languages, 
                sample_code,
                full_codebase
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
        except Exception as e:
            return {"error": f"Error analyzing project: {str(e)}"}
    
    def _generate_description(
        self, 
        repo_info: Dict[str, Any], 
        readme: str, 
        file_structure: Dict[str, Any], 
        languages: Dict[str, int], 
        sample_code: Dict[str, str],
        full_codebase: Dict[str, str]
    ) -> Dict[str, Any]:
        """Generate a comprehensive description of the project"""
        # Start with basic analysis
        description = {
            "summary": self._generate_summary(repo_info, readme, full_codebase),
            "architecture": self._analyze_architecture(file_structure, languages, full_codebase),
            "main_features": self._extract_features(readme, sample_code, full_codebase),
            "technologies": self._identify_technologies(languages, file_structure, readme, sample_code, full_codebase),
            "setup_instructions": self._extract_setup_instructions(readme),
            "code_quality": self._assess_code_quality(sample_code, full_codebase)
        }
        
        # Try to enhance with AI if API key is available
        if self.groq_api_key:
            ai_description = self._generate_ai_description(
                repo_info, readme, file_structure, languages, sample_code, full_codebase
            )
            if ai_description:
                description["ai_enhanced"] = ai_description
        
        return description
    
    def _generate_summary(self, repo_info: Dict[str, Any], readme: str, full_codebase: Dict[str, str]) -> str:
        """Generate a summary of the project using readme and code analysis"""
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
        
        # If still no good summary, try to analyze main files from the codebase
        if summary == "No description provided." or len(summary) < 50:
            important_files = self._identify_important_files(full_codebase, {})
            
            # Look for module or class docstrings in important files
            for file_path, content in important_files.items():
                # Python module/class docstrings
                if file_path.endswith('.py'):
                    docstring_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
                    if docstring_match:
                        docstring = docstring_match.group(1).strip()
                        if len(docstring) > 50:
                            summary = f"{docstring} (Extracted from code)"
                            break
                
                # JS file description comments
                if file_path.endswith('.js'):
                    js_comment = re.search(r'/\*\*(.*?)\*/', content, re.DOTALL)
                    if js_comment:
                        comment = js_comment.group(1).strip()
                        if len(comment) > 50:
                            summary = f"{comment} (Extracted from code)"
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
    
    def _analyze_architecture(self, file_structure: Dict[str, Any], languages: Dict[str, int], full_codebase: Dict[str, str]) -> str:
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
        
        # Analyze code structure for architectural patterns
        if full_codebase:
            framework_patterns = {
                "MVC": [r'models\.py', r'views\.py', r'controllers?\.py', r'routes\.py'],
                "Flask": [r'@app\.route', r'flask\.Flask', r'flask_'],
                "Django": [r'django\.', r'urls\.py', r'views\.py', r'models\.py', r'admin\.py'],
                "FastAPI": [r'fastapi\.', r'@app\.get', r'@app\.post'],
                "Express": [r'express\(', r'app\.use\(', r'app\.get\(', r'app\.post\('],
                "React": [r'import React', r'React\.Component', r'useState', r'useEffect'],
                "Angular": [r'@Component', r'@NgModule', r'@Injectable'],
                "Vue": [r'new Vue\(', r'Vue\.component', r'export default {'],
                "Microservices": [r'service', r'api.gateway', r'eureka', r'discovery', r'kafka', r'rabbitmq'],
                "RESTful API": [r'@RestController', r'REST', r'API', r'GET', r'POST', r'PUT', r'DELETE'],
                "ORM": [r'Entity', r'Table', r'Column', r'repository', r'ORM', r'sequelize', r'sqlalchemy']
            }
            
            detected_patterns = []
            for pattern_name, patterns in framework_patterns.items():
                # Check file names first
                if any(re.search(pattern, filepath) for pattern in patterns for filepath in full_codebase.keys()):
                    detected_patterns.append(pattern_name)
                    continue
                
                # Check file contents
                if any(re.search(pattern, content, re.IGNORECASE) for pattern in patterns for content in full_codebase.values()):
                    if pattern_name not in detected_patterns:
                        detected_patterns.append(pattern_name)
            
            if detected_patterns:
                architecture += "\nDetected architectural patterns and frameworks:\n"
                for pattern_name in detected_patterns:
                    architecture += f"- {pattern_name}\n"
        
        # Language distribution
        if languages:
            total = sum(languages.values())
            architecture += "\nLanguage distribution:\n"
            for lang, bytes_count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
                percentage = (bytes_count / total) * 100
                architecture += f"- {lang}: {percentage:.1f}%\n"
        
        # Analyze code structure from full codebase
        if full_codebase:
            # Count files per extension
            extensions = {}
            for file_path in full_codebase.keys():
                if "." in file_path:
                    ext = file_path.split(".")[-1].lower()
                    extensions[ext] = extensions.get(ext, 0) + 1
            
            if extensions:
                architecture += "\nFile types breakdown:\n"
                for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:10]:
                    architecture += f"- .{ext}: {count} files\n"
        
        return architecture
    
    def _extract_features(self, readme: str, sample_code: Dict[str, str], full_codebase: Dict[str, str]) -> List[str]:
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
                    features.extend(f"{f.strip()}" for f in bullet_features if f.strip())
        
        # If no features found in specific sections, try to guess from README
        if not features:
            # Look for bullet points that might describe features
            bullet_features = re.findall(r'[-*]\s+([A-Z].*?\.)', readme)
            features.extend(bullet_features[:5])  # Limit to first 5 potential features
        
        # Try to find features in code
        if not features and full_codebase:
            # Look for class and function definitions in Python files
            py_functions = []
            for file_path, content in full_codebase.items():
                if file_path.endswith('.py'):
                    # Skip test files
                    if 'test_' in file_path.lower() or 'tests/' in file_path.lower():
                        continue
                    
                    # Look for class definitions
                    class_matches = re.findall(r'class\s+(\w+)[\(:]', content)
                    for cls in class_matches:
                        if not cls.startswith('_') and not cls.lower().startswith('test'):
                            py_functions.append(f"'{cls}' class")
                    
                    # Look for function definitions
                    func_matches = re.findall(r'def\s+(\w+)\(', content)
                    for func in func_matches:
                        if not func.startswith('_') and not func.lower().startswith('test'):
                            py_functions.append(f"'{func}' functionality")
            
            # Add top Python functions as features
            features.extend(py_functions[:5])
        
        # Add generic features if nothing specific found
        if not features:
            main_lang = self._identify_main_language(sample_code, full_codebase)
            if main_lang == "Python":
                features = ["Python-based application", "Modular structure", "Command-line interface"]
            elif main_lang == "JavaScript":
                features = ["JavaScript-based application", "Web interface", "Modern JS architecture"]
            else:
                features = ["Software application", "Structured codebase", "Developer-friendly"]
        
        # Remove duplicates while preserving order
        unique_features = []
        seen = set()
        for feature in features:
            if feature.lower() not in seen:
                unique_features.append(feature)
                seen.add(feature.lower())
        
        return unique_features[:7]  # Limit to 7 most important features
    
    def _identify_technologies(
        self, 
        languages: Dict[str, int], 
        file_structure: Dict[str, Any], 
        readme: str, 
        sample_code: Dict[str, str],
        full_codebase: Dict[str, str]
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
        code_str = str(full_codebase) if full_codebase else ""
        
        # Python frameworks
        if "Django" in files_str or "django" in files_str or "django" in code_str:
            technologies["frameworks"].append("Django")
        if "Flask" in files_str or "flask" in files_str or "flask" in code_str:
            technologies["frameworks"].append("Flask")
        if "FastAPI" in files_str or "fastapi" in files_str or "fastapi" in code_str:
            technologies["frameworks"].append("FastAPI")
        
        # JavaScript frameworks
        if "react" in files_str or "React" in code_str:
            technologies["frameworks"].append("React")
        if "angular" in files_str or "Angular" in code_str:
            technologies["frameworks"].append("Angular")
        if "vue" in files_str or "Vue" in code_str:
            technologies["frameworks"].append("Vue.js")
        if "next.js" in files_str.lower() or "next" in files_str or "next" in code_str:
            technologies["frameworks"].append("Next.js")
        
        # Database technologies
        if "mongo" in files_str.lower() or "mongo" in code_str.lower():
            technologies["libraries"].append("MongoDB")
        if "postgres" in files_str.lower() or "postgres" in code_str.lower():
            technologies["libraries"].append("PostgreSQL")
        if "mysql" in files_str.lower() or "mysql" in code_str.lower():
            technologies["libraries"].append("MySQL")
        if "sqlite" in files_str.lower() or "sqlite" in code_str.lower():
            technologies["libraries"].append("SQLite")
        
        # Build tools
        if "webpack" in files_str.lower() or "webpack" in code_str.lower():
            technologies["tools"].append("Webpack")
        if "vite" in files_str.lower() or "vite" in code_str.lower():
            technologies["tools"].append("Vite")
        if "gulp" in files_str.lower() or "gulp" in code_str.lower():
            technologies["tools"].append("Gulp")
        
        # Testing frameworks
        if "jest" in files_str.lower() or "jest" in code_str.lower():
            technologies["tools"].append("Jest")
        if "pytest" in files_str.lower() or "pytest" in code_str.lower():
            technologies["tools"].append("pytest")
        if "mocha" in files_str.lower() or "mocha" in code_str.lower():
            technologies["tools"].append("Mocha")
        
        # More detailed analysis based on full codebase
        if full_codebase:
            # Look for imports in Python code
            python_imports = set()
            for file_path, code in full_codebase.items():
                if file_path.endswith('.py'):
                    imports = re.findall(r'import (\w+)|from (\w+)', code)
                    for match in imports:
                        imp = match[0] or match[1]
                        if imp and imp not in ["os", "sys", "re", "json", "time", "math", "random", "typing"]:
                            python_imports.add(imp)
            
            # Look for npm packages
            js_imports = set()
            for file_path, code in full_codebase.items():
                if file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                    imports = re.findall(r'require\([\'"]([^\'"]+)[\'"]\)|from\s+[\'"]([^\'"]+)[\'"]', code)
                    for match in imports:
                        imp = match[0] or match[1]
                        if imp and not imp.startswith("."):
                            # Clean package names (remove paths)
                            pkg = imp.split("/")[0]
                            js_imports.add(pkg)
            
            # Add to libraries
            for imp in python_imports:
                if imp not in technologies["libraries"]:
                    technologies["libraries"].append(imp)
            
            for imp in js_imports:
                if imp not in technologies["libraries"]:
                    technologies["libraries"].append(imp)
        
        # Also check sample code for backward compatibility
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
    
    def _assess_code_quality(self, sample_code: Dict[str, str], full_codebase: Dict[str, str]) -> str:
        """Perform a basic code quality assessment"""
        # Prefer full codebase if available
        code_to_assess = full_codebase if full_codebase else sample_code
        
        if not code_to_assess or all(val.startswith("Could not retrieve") for val in code_to_assess.values()):
            return "Could not assess code quality due to limited access to code files."
        
        quality_assessment = "Code quality assessment:\n\n"
        
        # Look for code smells and good practices
        total_length = 0
        comment_lines = 0
        long_lines = 0
        complex_functions = 0
        test_files = 0
        docstrings = 0
        
        for file_path, code in code_to_assess.items():
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
                # Count docstrings
                docstrings += len(re.findall(r'""".*?"""', code, re.DOTALL))
                
                # Look for Python functions with many lines
                python_funcs = re.findall(r'def\s+\w+\([^)]*\):\s*\n((?:\s+.+\n)+)', code)
                for func in python_funcs:
                    if func.count('\n') > 30:
                        complex_functions += 1
            elif '.js' in file_path or '.jsx' in file_path or '.ts' in file_path:
                # Look for JS functions with many lines
                js_funcs = re.findall(r'function\s+\w+\([^)]*\)\s*{((?:.+\n)+?)}', code)
                js_funcs.extend(re.findall(r'=>\s*{((?:.+\n)+?)}', code))
                for func in js_funcs:
                    if func.count('\n') > 30:
                        complex_functions += 1
            
            # Count test files
            if 'test' in file_path.lower() or 'spec' in file_path.lower():
                test_files += 1
        
        # Calculate metrics
        if total_length > 0:
            comment_ratio = (comment_lines / total_length) * 100
            long_lines_ratio = (long_lines / total_length) * 100
            
            quality_assessment += f"- Documentation: {'Good' if comment_ratio > 15 else 'Average' if comment_ratio > 5 else 'Minimal'} ({comment_ratio:.1f}% comment lines)\n"
            quality_assessment += f"- Code readability: {'Good' if long_lines_ratio < 5 else 'Average' if long_lines_ratio < 15 else 'Could be improved'} ({long_lines_ratio:.1f}% long lines)\n"
            quality_assessment += f"- Complexity: {'Low' if complex_functions == 0 else 'Medium' if complex_functions < 3 else 'High'} ({complex_functions} potentially complex functions)\n"
            
            if test_files > 0:
                quality_assessment += f"- Testing: Project includes {test_files} test files\n"
        else:
            quality_assessment += "- Insufficient code available for quality assessment\n"
        
        # Look for good practices
        good_practices = []
        if test_files > 0:
            good_practices.append("Evidence of testing")
        
        if docstrings > 0:
            good_practices.append(f"{docstrings} docstrings found")
            
        if "type" in str(code_to_assess).lower() and (":" in str(code_to_assess) or "TypeScript" in str(code_to_assess)):
            good_practices.append("Type annotations")
        
        if "exception" in str(code_to_assess).lower() or "try" in str(code_to_assess).lower():
            good_practices.append("Exception handling")
        
        if good_practices:
            quality_assessment += "- Good practices observed: " + ", ".join(good_practices) + "\n"
        
        return quality_assessment
    
    def _identify_main_language(self, sample_code: Dict[str, str], full_codebase: Dict[str, str] = None) -> str:
        """Identify the main programming language based on sample code or full codebase"""
        # Prefer full codebase if available
        code_to_assess = full_codebase if full_codebase else sample_code
        
        extensions = []
        for file_path in code_to_assess.keys():
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
            "jsx": "JavaScript (React)",
            "ts": "TypeScript",
            "tsx": "TypeScript (React)",
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
        sample_code: Dict[str, str],
        full_codebase: Dict[str, str] = None
    ) -> Optional[Dict[str, str]]:
        """Use Groq API to generate an enhanced description with code workflow analysis"""
        if not self.groq_api_key:
            return None
        
        try:
            # Prepare data for AI analysis
            context = {
                "name": repo_info.get("name", ""),
                "description": repo_info.get("description", ""),
                "readme_excerpt": readme[:5000] if readme else "",
                "languages": str(languages),
                "file_structure": str(file_structure)[:2000],
            }
            
            # Include more code information
            code_context = ""
            important_files = {}
            
            # Use full codebase if available, otherwise use sample code
            code_to_analyze = full_codebase if full_codebase else sample_code
            
            # Get important files for analysis
            important_files = self._identify_important_files(code_to_analyze, file_structure)
            
            for path, content in important_files.items():
                # Truncate very large files but provide enough context
                file_content = content[:10000] if len(content) > 10000 else content
                code_context += f"\n\n--- {path} ---\n{file_content}"
            
            prompt = f"""
            Your task is to perform a deep analysis of this GitHub project's code structure, workflow, and implementation details.
            
            Project name: {context['name']}
            Project description: {context['description']}
            
            README excerpt:
            {context['readme_excerpt']}
            
            Languages used:
            {context['languages']}
            
            File structure excerpt:
            {context['file_structure']}
            
            CODE ANALYSIS:
            {code_context[:50000]}  # Limit total code context
            
            Based on the provided code and information, please provide:
            
            1. High-level summary of the project's purpose (2-3 sentences)
            2. Main features (3-5 bullet points)
            3. Detailed workflow analysis: How does the code flow through the application? Identify the entry points, core logic, and data flows.
            4. Code architecture: Identify the architectural patterns used (MVC, microservices, etc.) and how the codebase is organized
            5. Key dependencies and their purposes
            6. Technical strengths and potential improvements
            7. Setup process: How would a developer run this project locally?
            """
            
            # Make API call to Groq
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama3-8b-8192",  # or a larger model if needed
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 2000
                },
                timeout=30  # Add timeout to prevent hanging
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                if not ai_content:
                    return None
                
                # Parse the AI response
                sections = re.split(r'\n\d+\.\s+', ai_content)
                
                if len(sections) >= 7:  # We need at least 7 sections (skip the first empty one)
                    return {
                        "summary": sections[1].strip() if len(sections) > 1 else "",
                        "features": sections[2].strip() if len(sections) > 2 else "",
                        "workflow": sections[3].strip() if len(sections) > 3 else "",
                        "architecture": sections[4].strip() if len(sections) > 4 else "",
                        "dependencies": sections[5].strip() if len(sections) > 5 else "",
                        "assessment": sections[6].strip() if len(sections) > 6 else "",
                        "setup": sections[7].strip() if len(sections) > 7 else ""
                    }
            
            return None
        except Exception as e:
            print(f"Error generating AI description: {str(e)}")
            return None

    def _identify_important_files(self, codebase: Dict[str, str], file_structure: Dict[str, Any]) -> Dict[str, str]:
        """Identify the most important files for understanding the project"""
        important_files = {}
        
        if not codebase:
            return important_files
        
        # Common patterns for important files
        patterns = [
            # Entry points
            r'main\.py$', r'app\.py$', r'index\.js$', r'server\.js$', 
            # Configuration
            r'settings\.py$', r'config\.py$', r'package\.json$', r'requirements\.txt$',
            # Core logic
            r'views\.py$', r'models\.py$', r'controllers\.js$', r'routes\.js$',
            # Workflow definition
            r'workflow\.py$', r'pipeline\.py$', r'process\.js$'
        ]
        
        # First pass: get files matching patterns
        for path, content in codebase.items():
            if any(re.search(pattern, path) for pattern in patterns):
                if not content.startswith("Could not retrieve"):
                    important_files[path] = content
        
        # Second pass: if we didn't get enough files, include more based on file structure
        if len(important_files) < 5:
            # Find Python/JavaScript files at the root or key directories
            key_exts = ['.py', '.js', '.jsx', '.ts', '.tsx']
            for file_path, content in codebase.items():
                if any(file_path.endswith(ext) for ext in key_exts):
                    # Skip test files
                    if 'test_' in file_path or '/tests/' in file_path:
                        continue
                    
                    # Prioritize files in src, app, or root directories
                    if 'src/' in file_path or 'app/' in file_path or '/' not in file_path:
                        if file_path not in important_files and not content.startswith("Could not retrieve"):
                            important_files[file_path] = content
                            if len(important_files) >= 10:
                                break
        
        # Third pass: If still not enough, pick files based on size and name
        if len(important_files) < 5:
            # Sort by file size (approximated by content length)
            file_sizes = [(path, len(content)) for path, content in codebase.items() 
                         if path not in important_files and not content.startswith("Could not retrieve")]
            
            # Add top files by size (avoiding test files and small files)
            for path, size in sorted(file_sizes, key=lambda x: x[1], reverse=True):
                if size > 100 and 'test_' not in path and '/tests/' not in path:
                    important_files[path] = codebase[path]
                    if len(important_files) >= 10:
                        break
        
        # Return at most 10 important files to keep the context manageable
        return dict(list(important_files.items())[:10])