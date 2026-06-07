# Improvement to Inkeep – AI Response Authentication Monitor

## Overview

AI support agents can sometimes generate answers that look correct but contain factual mistakes. These "silent hallucinations" are especially dangerous for developer tools because users may follow incorrect code snippets or configurations and lose trust in the product.

This project is a lightweight AI Response Authentication Monitor that continuously evaluates AI-generated responses against official documentation and flags potential hallucinations for review.

## Problem Statement

Technical AI assistants occasionally provide incorrect answers that appear believable. Manually reviewing thousands of conversations is slow, expensive, and difficult to scale.

The goal of this project is to automatically identify potentially inaccurate responses and provide visibility into the overall health and reliability of the AI system.

## Solution

The system acts as an independent monitoring layer:

1. Receives a developer query, AI response, and corresponding documentation.
2. Uses Gemini to compare the response against the ground-truth documentation.
3. Generates an accuracy score and evaluation status.
4. Flags suspicious responses for human review.
5. Displays results in a centralized dashboard.

Unlike real-time verification systems, this monitor operates asynchronously and does not introduce latency into the user experience.

## Features

* AI-powered response evaluation
* Hallucination detection
* Accuracy scoring
* Verification status tracking
* Real-time evaluation dashboard
* Searchable evaluation logs
* Live testing sandbox
* Documentation vs Response comparison

## Tech Stack

### Backend

* Python
* Flask
* Gemini API

### Frontend

* HTML
* CSS
* JavaScript

### AI Evaluation

* Gemini 2.5 Flash / Gemini 2.5 Pro

## Dashboard Metrics

* Total Evaluated Responses
* System Health Score
* Flagged Anomalies
* Average Accuracy
* Evaluation Log Feed
* Verification Status Tracking

## Example Workflow

Developer Query:

```text
What timeout should I use for InkeepWidget and what's the default?
```

Documentation:

```text
Default timeout is 30 seconds.
```

AI Response:

```text
Default timeout is 60 seconds.
```

Evaluation Result:

```text
Accuracy: 15%
Status: FLAGGED
Reason: Response contradicts official documentation.
```

## Future Improvements

* Integration with production chat systems
* Automatic documentation gap detection
* Trend analysis for recurring hallucinations
* Multi-model evaluation support
* Slack and email alerts
* Historical analytics dashboard

## Installation

```bash
git clone https://github.com/CodingMava/Improvement-to-Inkeep.git
cd Improvement-to-Inkeep

pip install -r requirements.txt
python app.py
```

## Motivation

This project explores how AI can be used not only to generate answers, but also to evaluate and monitor the quality of other AI systems. By automatically identifying hallucinations and factual inconsistencies, teams can improve trust, reliability, and developer experience.
