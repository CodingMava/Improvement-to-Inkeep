import os
import time
import json
import re
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# Load .env variables if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


app = Flask(__name__)
CORS(app)

# Pulls the key dynamically from your terminal environment
API_KEY = os.environ.get("GEMINI_API_KEY")
print(f"API_KEY LOADED: {API_KEY is not None}")
if API_KEY:
    print(f"API_KEY LENGTH: {len(API_KEY)}")
    print(f"API_KEY REPR: {API_KEY[:5]}...{API_KEY[-5:] if len(API_KEY) > 5 else ''}")


# In-memory database of evaluations, pre-populated with sample entries for demo purposes
evaluations_db = [
    {
        "id": "req_1",
        "timestamp": int(time.time()) - 3600,
        "query": "How do I mount the Inkeep widget?",
        "docs": "The Inkeep SDK requires Node.js v18+. To initialize the widget, call `InkeepWidget.mount({ apiKey: 'your_key' })`. The default timeout is 30 seconds.",
        "agent_response": "To mount the widget, import the SDK and call `InkeepWidget.mount({ apiKey: 'your_key' })`.",
        "score": 0.98,
        "status": "Verified",
        "issue": "None",
        "reasoning": "The agent response correctly references the initialization method `InkeepWidget.mount` with the parameter `apiKey` matching the ground truth documentation.",
        "mocked": True
    },
    {
        "id": "req_2",
        "timestamp": int(time.time()) - 1800,
        "query": "What is the timeout for the widget mount?",
        "docs": "The Inkeep SDK requires Node.js v18+. To initialize the widget, call `InkeepWidget.mount({ apiKey: 'your_key' })`. The default timeout is 30 seconds.",
        "agent_response": "The default timeout for the Inkeep widget mount function is 60 seconds.",
        "score": 0.65,
        "status": "Review",
        "issue": "Timeout discrepancy: Agent stated 60 seconds, documentation states 30 seconds.",
        "reasoning": "The agent response incorrectly states the default timeout is 60 seconds. The ground truth documentation specifies the default timeout is 30 seconds.",
        "mocked": True
    },
    {
        "id": "req_3",
        "timestamp": int(time.time()) - 600,
        "query": "Is there a method to destroy all active widgets?",
        "docs": "The Inkeep SDK requires Node.js v18+. To initialize the widget, call `InkeepWidget.mount({ apiKey: 'your_key' })`. The default timeout is 30 seconds.",
        "agent_response": "Yes, you can destroy all active widgets by calling the `InkeepWidget.destroyAll()` method.",
        "score": 0.15,
        "status": "Flagged",
        "issue": "Hallucinated method: InkeepWidget.destroyAll() does not exist in documentation.",
        "reasoning": "The agent response claims `InkeepWidget.destroyAll()` can be used to destroy all active widgets. The ground truth documentation has no mention of this method, making it a critical hallucination.",
        "mocked": True
    }
]

@app.route('/api/evaluations', methods=['GET'])
def get_evaluations():
    return jsonify(evaluations_db)


@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    if not evaluations_db:
        return jsonify({
            "total_queries": 0,
            "verified_count": 0,
            "review_count": 0,
            "flagged_count": 0,
            "avg_accuracy": 0.0,
            "health_rate": 100.0
        })
    
    total = len(evaluations_db)
    verified = sum(1 for e in evaluations_db if e['status'] == 'Verified')
    review = sum(1 for e in evaluations_db if e['status'] == 'Review')
    flagged = sum(1 for e in evaluations_db if e['status'] == 'Flagged')
    avg_accuracy = sum(e['score'] for e in evaluations_db) / total
    
    # Health Rate is percentage of non-flagged queries weighted by score
    health_rate = ((verified + review * 0.5) / total) * 100 if total > 0 else 100.0
    
    return jsonify({
        "total_queries": total,
        "verified_count": verified,
        "review_count": review,
        "flagged_count": flagged,
        "avg_accuracy": avg_accuracy,
        "health_rate": health_rate
    })

def run_heuristic_evaluation(docs, user_query, agent_response, warning_note=None):
    score = 0.98
    status = "Verified"
    issue = "None"
    reasoning = "Used local rule-based heuristic check."

    # 1. Check for numerical mismatches (e.g. timeout values, versions, ports)
    agent_nums = re.findall(r'\b\d+\b', agent_response)
    docs_nums = re.findall(r'\b\d+\b', docs)
    unsupported_nums = [num for num in agent_nums if num not in docs_nums]

    # 2. Check for code/method hallucinations (e.g. InkeepWidget.destroyAll() or destroyAll())
    agent_code_snippets = re.findall(r'`([^`]+)`', agent_response)
    agent_fn_calls = re.findall(r'\b[A-Za-z0-9_]+\.[A-Za-z0-9_]+(?:\(\))?\b|\b[A-Za-z0-9_]+\(\)\b', agent_response)
    all_agent_codes = set(agent_code_snippets + agent_fn_calls)
    
    hallucinated_methods = []
    for code in all_agent_codes:
        clean_code = code.replace("()", "").strip()
        parts = clean_code.split('.')
        for part in parts:
            if len(part) > 4 and part not in docs:
                hallucinated_methods.append(code)
                break

    # 3. Check for semantic relevance (keyword overlap check)
    stopwords = {
        'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'to', 'for', 
        'in', 'on', 'at', 'by', 'with', 'from', 'of', 'you', 'your', 'i', 'we', 'they', 
        'he', 'she', 'it', 'can', 'will', 'should', 'would', 'do', 'does', 'did', 'have', 
        'has', 'had', 'be', 'been', 'this', 'that', 'these', 'those', 'how', 'what', 'which',
        'who', 'whom', 'then', 'there', 'their', 'them', 'here', 'out', 'off'
    }
    
    agent_words = set(re.findall(r'\b[a-z]{3,}\b', agent_response.lower()))
    meaningful_agent_words = agent_words - stopwords
    
    docs_words = set(re.findall(r'\b[a-z]{3,}\b', docs.lower()))
    query_words = set(re.findall(r'\b[a-z]{3,}\b', user_query.lower()))
    context_words = docs_words.union(query_words) - stopwords
    
    irrelevant_response = False
    if meaningful_agent_words:
        overlap = meaningful_agent_words.intersection(context_words)
        if not overlap:
            irrelevant_response = True
    else:
        irrelevant_response = True

    # Determine status using heuristics
    if irrelevant_response:
        score = 0.10
        status = "Flagged"
        issue = "Irrelevant response: The answer shares no technical or contextual words with the documentation or query."
        reasoning = f"Heuristic check: The agent response '{agent_response}' appears entirely unrelated to the documentation or query context."
    elif hallucinated_methods:
        score = 0.15
        status = "Flagged"
        issue = f"Hallucinated API reference: {', '.join(hallucinated_methods)} not found in documentation."
        reasoning = f"Heuristic check: The agent response references API methods or code snippets ({hallucinated_methods}) that do not exist in the ground-truth documentation."
    elif unsupported_nums:
        score = 0.65
        status = "Review"
        issue = f"Numerical discrepancy: Agent stated parameter(s) {', '.join(unsupported_nums)} not found in documentation."
        reasoning = f"Heuristic check: Found numerical values in the agent response ({unsupported_nums}) that are not present in the ground-truth documentation. Please verify timeout, port, or version parameters."
    elif len(agent_response) < 15:
        score = 0.40
        status = "Flagged"
        issue = "Response is too brief to contain factual value."
        reasoning = "Heuristic check: The agent response is extremely brief and does not adequately answer the developer query based on documentation."

    if warning_note:
        reasoning += f" (Note: {warning_note})"


    eval_data = {
        "id": f"req_{int(time.time())}",
        "timestamp": int(time.time()),
        "query": user_query,
        "docs": docs,
        "agent_response": agent_response,
        "score": score,
        "status": status,
        "issue": issue,
        "reasoning": reasoning,
        "mocked": True
    }
    evaluations_db.insert(0, eval_data)
    return eval_data


@app.route('/api/evaluate', methods=['POST'])
def evaluate_response():
    data = request.json or {}
    docs = data.get('docs', '').strip()
    user_query = data.get('query', '').strip()
    agent_response = data.get('agent_response', '').strip()

    if not all([docs, user_query, agent_response]):
        return jsonify({"error": "Missing required fields: docs, query, and agent_response are required."}), 400

    # If API key is missing, fall back to mock heuristics
    if not API_KEY:
        time.sleep(1.0)  # Simulate network latency
        eval_data = run_heuristic_evaluation(docs, user_query, agent_response, "GEMINI_API_KEY env variable is missing")
        return jsonify(eval_data)

    eval_prompt = f"""
    You are a strict technical auditor. Compare the Agent's Response to the Ground Truth Documentation.
    Check for factual inaccuracies, incorrect parameters, hallucinated function names, and obsolete settings.
    
    Ground Truth Docs: {docs}
    User Query: {user_query}
    Agent's Response: {agent_response}
    
    Evaluate the response and output a JSON object matching this schema:
    {{
        "score": float (between 0.0 and 1.0 representing accuracy, where 1.0 is completely accurate and 0.0 is completely hallucinated),
        "status": string ("Verified", "Review", or "Flagged"),
        "issue": string ("None" or description of inaccuracy),
        "reasoning": string (explanation of the audit reasoning)
    }}
    
    Keep the status rules:
    - "Verified": Score >= 0.9, no technical issues or minor formatting differences only.
    - "Review": Score 0.6 - 0.89, minor technical inaccuracies, outdated parameters, or questionable assertions.
    - "Flagged": Score < 0.6, critical hallucinations, inventing APIs, or conflicting direct facts.
    """

    # Determine authorization style dynamically (standard AI Studio key vs OAuth Bearer token)
    if API_KEY.startswith("AIzaSy"):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
        headers = {'Content-Type': 'application/json'}
    else:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {API_KEY}'
        }

    payload = {
        "contents": [{"parts": [{"text": eval_prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        result = response.json()
        
        # If the API returned an authentication or model support error, fall back to heuristic instead of crash
        if 'error' in result:
             err_msg = result['error']['message']
             print(f"Gemini API Error: {err_msg}. Falling back to rule-based heuristics.")
             eval_data = run_heuristic_evaluation(docs, user_query, agent_response, f"Gemini API returned error: {err_msg}")
             return jsonify(eval_data)

        raw_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
        eval_data = json.loads(raw_text)
        
        # Add metadata fields
        eval_data["id"] = f"req_{int(time.time())}"
        eval_data["timestamp"] = int(time.time())
        eval_data["query"] = user_query
        eval_data["docs"] = docs
        eval_data["agent_response"] = agent_response
        eval_data["mocked"] = False
        
        # Standard default fallbacks
        if "score" not in eval_data:
            eval_data["score"] = 0.5
        if "status" not in eval_data:
            eval_data["status"] = "Review"
        if "issue" not in eval_data:
            eval_data["issue"] = "Failed to parse issue details."
        if "reasoning" not in eval_data:
            eval_data["reasoning"] = "No audit explanation provided by Gemini."
            
        evaluations_db.insert(0, eval_data)
        return jsonify(eval_data)

    except Exception as e:
        print(f"Exception during Gemini API call: {str(e)}. Falling back to rule-based heuristics.")
        eval_data = run_heuristic_evaluation(docs, user_query, agent_response, f"Network/Internal exception: {str(e)}")
        return jsonify(eval_data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)