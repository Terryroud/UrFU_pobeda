# Task: Refactor application into microservices with centralized logging

## Overview
Refactor the existing monolithic application into three FastAPI microservices:
- RAG microservice: handles RAG model operations
- YandexGPTBot microservice: handles bot operations
- Logging microservice: centralized logging service to collect and store logs from all microservices

The main.py will be refactored to orchestrate calls to these microservices, preserving the existing functionality.

## Detailed Steps

### 1. Create Logging Microservice ✅
- Create a FastAPI app exposing an endpoint `/log` to receive log messages (level, message, timestamp, service name)
- Store logs in a centralized location (e.g., log files with rotation)
- Provide a simple health check endpoint

### 2. Create RAG Microservice ✅
- Extract RAG class logic into a FastAPI app
- Expose endpoints for:
  - Creating FAISS index (`/create_index`)
  - Querying RAG (`/query`)
- Send logs to logging microservice via HTTP calls

### 3. Create YandexGPTBot Microservice ✅
- Extract YandexGPTBot class logic into a FastAPI app
- Expose endpoints for:
  - Getting IAM token (`/iam_token`)
  - Asking GPT (`/ask_gpt`)
- Send logs to logging microservice via HTTP calls

### 4. Refactor main.py
- Remove local RAG and YandexGPTBot instances
- Implement HTTP client calls to RAG and YandexGPTBot microservices
- Send logs to logging microservice
- Keep Telegram bot logic intact, but delegate processing to microservices

### 5. Setup and Run
- Provide instructions or scripts to run all microservices concurrently
- Test end-to-end functionality to ensure the bot works as before

## Follow-up
- Verify environment variables are properly set for each microservice
- Ensure error handling and retries for HTTP calls
- Dockerize the Application ✅
  - Create Dockerfiles for each microservice
  - Create docker-compose.yml to orchestrate all services
  - Ensure proper service dependencies and networking

---

This plan will be executed step-by-step, starting with the logging microservice.
