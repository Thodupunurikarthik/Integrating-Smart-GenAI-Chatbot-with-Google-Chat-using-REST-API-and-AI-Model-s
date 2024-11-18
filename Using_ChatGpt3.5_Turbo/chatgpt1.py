from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from pydantic import BaseModel
import json
import os
import openai  # type: ignore # Import OpenAI client for ChatGPT API integration

app = FastAPI()

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins, replace with specific domains for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path for JSON data
ISSUES_FILE_PATH = "network_issues.json"

# Load issues from JSON
def load_issues() -> List[dict]:
    if os.path.exists(ISSUES_FILE_PATH):
        with open(ISSUES_FILE_PATH, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []  # Return an empty list if JSON is invalid
    return []

# Save issues to JSON
def save_issues(issues: List[dict]):
    with open(ISSUES_FILE_PATH, "w") as f:
        json.dump(issues, f, indent=4)

# Define the data model for issues
class Issue(BaseModel):
    id: int
    title: str
    problem: str
    cause: str
    solution: str
    keywords: List[str]

# Utility function to format issues for output
def format_issue(issue: dict) -> str:
    return (
        f"**Issue ID**: {issue['id']}\n"
        f"**Title**: {issue['title']}\n"
        f"**Problem**: {issue['problem']}\n"
        f"**Cause**: {issue['cause']}\n"
        f"**Solution**: {issue['solution']}\n"
        f"**Keywords**: {', '.join(issue['keywords'])}\n"
        "----------------------------------------"
    )

# Initialize OpenAI client with API key for ChatGPT
openai.api_key = "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"  # Replace with your OpenAI API key

# Fetch response from ChatGPT-3.5 Turbo
def get_chatgpt_response(prompt: str) -> str:
    try:
        # Call the OpenAI API using ChatGPT-3.5 Turbo model
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=1,
            max_tokens=1024,
            top_p=1
        )
        
        response_text = completion.choices[0].message['content']
        return response_text

    except Exception as e:
        return f"Error contacting ChatGPT-3.5 Turbo: {str(e)}"

# Create a new issue using ChatGPT-3.5 Turbo if none is found
def create_issue_from_chatgpt(query: str, issues: List[dict]) -> dict:
    prompt = f"Could you help me understand the issue related to: {query}?"
    chatgpt_response = get_chatgpt_response(prompt)
    
    # Generate a new issue ID based on existing issues
    new_issue_id = max([issue["id"] for issue in issues], default=0) + 1
    new_issue = {
        "id": new_issue_id,
        "title": f"Generated Issue for '{query}'",
        "problem": query,
        "cause": "Generated by ChatGPT-3.5 Turbo",
        "solution": chatgpt_response,
        "keywords": [keyword.strip() for keyword in query.split()]
    }

    # Add the new issue to the list and save it
    issues.append(new_issue)
    save_issues(issues)
    return new_issue

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the Network Issues Chatbot API with ChatGPT-3.5 Turbo integration"}

# Search issues by query
def search_issues(query: str, issues: List[dict]) -> List[dict]:
    query_lower = query.lower()
    return [
        issue for issue in issues
        if (issue.get('title') and query_lower in issue['title'].lower()) or 
           (issue.get('problem') and query_lower in issue['problem'].lower())
    ]

# Endpoint to get issues by query or use ChatGPT-3.5 Turbo if not found
@app.get("/issues")
def get_issue(query: Optional[str] = Query(None, description="Query for searching issues")):
    if not query:
        raise HTTPException(status_code=400, detail="Query parameter is required")
    
    issues = load_issues()
    results = search_issues(query, issues)
    
    if results:
        formatted_issues = "\n\n".join([format_issue(issue) for issue in results])
        return {"issues_found": formatted_issues}
    
    # No matching issues; create a new one using ChatGPT-3.5 Turbo
    new_issue = create_issue_from_chatgpt(query, issues)
    formatted_new_issue = format_issue(new_issue)
    return {
        "message": "No existing issue found. Created a new issue using ChatGPT-3.5 Turbo:",
        "structured_issue": formatted_new_issue
    }
