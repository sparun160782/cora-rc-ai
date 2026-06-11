---
title: "Google ADK with Runner Usage"
author: "Arun S.P"
last_updated: "2025-01-XX"
---

# Google ADK with Runner Usage

## 🎯 Direct Recommendation: Method 3 (Programmatic Runner)

**Method 3 (Programmatic Runner) is the clear winner for your requirements.** Here's why:

**Method 1 (CLI)** is not designed for server deployment—it's a terminal-based interface for manual testing only.

**Method 2 (Web UI)** explicitly states it's "for development only, not for production use." It lacks authentication, logging, and cannot be properly secured for production.

**Method 3 (Programmatic Runner)** gives you full control to build production APIs with FastAPI/Flask, deploy to GKE pods, implement SSE streaming, add authentication, metrics, and all enterprise requirements.

---

## Request–Response API vs. Real-Time Streaming (SSE)

### Request–Response API

**A traditional HTTP pattern where the client sends one request and waits for one complete response.**

**ADK Example using `run()` or `run_async()`:**

```python
from fastapi import FastAPI
from google.adk.runners import Runner
from my_agent.agent import root_agent

app = FastAPI()
runner = Runner(agent=root_agent)

@app.post("/chat")
async def chat(message: str):
    # Client waits until entire response is ready
    response = await runner.run_async(message)
    return {"response": response.text}  # Single JSON payload
```

**Flow:**

- Client sends: `POST /chat {"message": "Tell me a story"}`
- **Client waits 5-10 seconds** (entire story generated server-side)
- Server returns: `{"response": "Once upon a time... [full story]"}`
- Connection closes

**Drawback:** User sees nothing until the complete response is ready—poor UX for conversational AI.

---

### Real-Time Streaming (SSE - Server-Sent Events)

**A pattern where the server sends data incrementally as it becomes available, without closing the connection.**

**ADK Example using `run_live()`:**

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from google.adk.runners import Runner
from my_agent.agent import root_agent

app = FastAPI()
runner = Runner(agent=root_agent)

@app.post("/chat/stream")
async def chat_stream(message: str):
    async def event_generator():
        # Stream events as they arrive
        async for event in runner.run_live(message):
            if event.type == "text_chunk":
                # Send each token as it's generated
                yield f"data: {event.text}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

**Flow:**

- Client sends: `POST /chat/stream {"message": "Tell me a story"}`
- Server immediately responds with HTTP 200 and keeps connection open
- Server streams: `data: Once\n\n` → `data: upon\n\n` → `data: a\n\n` → `data: time\n\n`...
- **Client displays each word/token as it arrives** (ChatGPT-like experience)
- Connection closes when story completes

**Benefit:** Immediate feedback, perceived lower latency, better user experience for conversational AI.

---

## Method Comparison: GKE Production Focus

| Criterion | Method 1: CLI Runner | Method 2: Web UI Runner | Method 3: Programmatic Runner |
|-----------|----------------------|-------------------------|-------------------------------|
| GKE Pod Deployment | ❌ Not applicable | ⚠️ Possible but unsupported | ✅ **Primary use case** |
| SSE/Streaming Support | ❌ Terminal-only | ⚠️ WebSocket (not SSE standard) | ✅ **Full SSE via `run_live()`** |
| Horizontal Scaling | ❌ Single user | ❌ Not designed for scale | ✅ **Stateless pods + HPA** |
| Production Readiness | ❌ Dev/test only | ❌ **Explicitly not for production** | ✅ **Enterprise-grade** |
| Custom Auth | ❌ No | ❌ No | ✅ Full control (OAuth, IAM) |
| Observability | ❌ No | ❌ Basic logs | ✅ Prometheus, Cloud Trace, Logging |
| Session Management | N/A | In-memory only | ✅ Redis, Cloud SQL, Firestore |
| Dev→Prod Workflow | ❌ Separate codebases | ⚠️ Must rebuild for prod | ✅ **Same code, different config** |
| Latency | N/A | High (dev server) | ✅ Optimized for production |
| Cost | Free | Free | Pay-per-use (GKE nodes) |
| Setup Complexity | Minimal | Minimal | Moderate (requires API wrapper) |

---

## End-to-End GKE Reference Architecture

### Architecture Overview

### Component Details

**1. Containerized ADK Application (FastAPI)**

This is the core pod container running in GKE.

**Project structure:**

```
adk-agent-api/
├── Dockerfile
├── requirements.txt
├── main.py                 # FastAPI app with Runner
├── agent/
│   ├── __init__.py
│   └── agent.py            # ADK agent definition
└── k8s/
    ├── deployment.yaml
    ├── service.yaml
    └── ingress.yaml
```

**`main.py` - FastAPI with ADK Runner:**

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from google.adk.runners import Runner
from agent.agent import root_agent
import logging

# Initialize FastAPI
app = FastAPI(title="ADK Agent API")

# Initialize ADK Runner
runner = Runner(agent=root_agent)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Request model
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

# SSE Streaming endpoint (RECOMMENDED)
@app.post("/v1/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Real-time streaming chat using SSE.
    Provides token-by-token response for better UX.
    """
    try:
        async def event_generator():
            # Use run_live() for bidirectional streaming
            async for event in runner.run_live(request.message):
                # Stream different event types
                if event.type == "text_chunk":
                    yield f"data: {{'type': 'token', 'content': '{event.text}'}}\n\n"
                elif event.type == "tool_call":
                    yield f"data: {{'type': 'tool', 'name': '{event.tool_name}'}}\n\n"
                elif event.type == "complete":
                    yield f"data: {{'type': 'done'}}\n\n"
            
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Request-Response endpoint (OPTIONAL - for simple integrations)
@app.post("/v1/chat")
async def chat(request: ChatRequest):
    """
    Traditional request-response pattern.
    Returns complete response after full generation.
    """
    try:
        response = await runner.run_async(request.message)
        return {
            "response": response.text,
            "session_id": request.session_id
        }
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check for GKE probes
@app.get("/health")
async def health():
    return {"status": "healthy", "runner": "initialized"}

# Readiness check
@app.get("/ready")
async def ready():
    return {"status": "ready"}
```

**`agent/agent.py` - ADK Agent Definition:**

```python
from __future__ import annotations
from google.adk.agents import Agent

root_agent = Agent(
    name="production_assistant",
    model="gemini-2.0-flash",
    description="Production AI assistant with streaming support",
    instruction=(
        "You are a helpful AI assistant deployed on GKE. "
        "Provide accurate, concise responses. "
        "Use streaming for better user experience."
    )
)
```

**`Dockerfile` - Container Image:**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Run FastAPI with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]
```

**`requirements.txt`:**

```
google-adk>=2.2.0
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
```

---

### 2. Kubernetes Manifests

**`k8s/deployment.yaml` - GKE Deployment:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: adk-agent
  namespace: default
  labels:
    app: adk-agent
spec:
  replicas: 3  # Horizontal scaling
  selector:
    matchLabels:
      app: adk-agent
  template:
    metadata:
      labels:
        app: adk-agent
    spec:
      containers:
      - name: agent-api
        image: gcr.io/YOUR_PROJECT/adk-agent:latest
        ports:
        - containerPort: 8080
          name: http
        env:
        - name: GOOGLE_API_KEY
          valueFrom:
            secretKeyRef:
              name: adk-secrets
              key: google-api-key
        - name: ENVIRONMENT
          value: "production"
        
        # Resource limits
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "2000m"
            memory: "2Gi"
        
        # Health checks
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
      
      # Horizontal Pod Autoscaler (HPA) compatible
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - adk-agent
              topologyKey: kubernetes.io/hostname
```

**`k8s/service.yaml` - ClusterIP Service:**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: adk-agent-service
  namespace: default
  labels:
    app: adk-agent
spec:
  type: ClusterIP
  selector:
    app: adk-agent
  ports:
  - port: 80
    targetPort: 8080
    protocol: TCP
    name: http
  sessionAffinity: None  # Stateless design
```

**`k8s/ingress.yaml` - HTTPS Ingress with SSL:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: adk-agent-ingress
  namespace: default
  annotations:
    kubernetes.io/ingress.class: "gce"
    kubernetes.io/ingress.global-static-ip-name: "adk-agent-ip"
    networking.gke.io/managed-certificates: "adk-agent-cert"
    kubernetes.io/ingress.allow-http: "false"  # HTTPS only
spec:
  rules:
  - host: agent.yourdomain.com
    http:
      paths:
      - path: /*
        pathType: ImplementationSpecific
        backend:
          service:
            name: adk-agent-service
            port:
              number: 80
---
apiVersion: networking.gke.io/v1
kind: ManagedCertificate
metadata:
  name: adk-agent-cert
  namespace: default
spec:
  domains:
    - agent.yourdomain.com
```

**`k8s/hpa.yaml` - Horizontal Pod Autoscaler:**

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: adk-agent-hpa
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: adk-agent
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Pods
        value: 1
        periodSeconds: 60
```

---

### 3. Development to Production Workflow

**Detailed commands:**

```bash
# 1. LOCAL DEVELOPMENT
cd adk-agent-api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run locally
uvicorn main:app --reload --port 8000

# Test SSE streaming
curl -N -X POST http://localhost:8000/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me a story"}'

# 2. BUILD CONTAINER
docker build -t adk-agent:dev .

# Test container locally
docker run -p 8080:8080 \
  -e GOOGLE_API_KEY="your-key" \
  adk-agent:dev

# 3. PUSH TO GCR
gcloud auth configure-docker
docker tag adk-agent:dev gcr.io/YOUR_PROJECT/adk-agent:v1.0.0
docker push gcr.io/YOUR_PROJECT/adk-agent:v1.0.0

# 4. CREATE GKE CLUSTER (if needed)
gcloud container clusters create adk-cluster \
  --region=us-central1 \
  --num-nodes=3 \
  --machine-type=n2-standard-4 \
  --enable-autoscaling \
  --min-nodes=3 \
  --max-nodes=10 \
  --enable-autorepair \
  --enable-autoupgrade

# Get credentials
gcloud container clusters get-credentials adk-cluster --region=us-central1

# 5. CREATE SECRETS
kubectl create secret generic adk-secrets \
  --from-literal=google-api-key="YOUR_ACTUAL_API_KEY"

# 6. DEPLOY TO GKE
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml

# 7. VERIFY DEPLOYMENT
kubectl get pods -l app=adk-agent
kubectl get service adk-agent-service
kubectl get ingress adk-agent-ingress

# Check logs
kubectl logs -l app=adk-agent --tail=100 -f

# 8. TEST PRODUCTION ENDPOINT
# (Wait 10-15 min for SSL cert provisioning)
curl -N -X POST https://agent.yourdomain.com/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello from GKE!"}'
```

---

### 4. Production Enhancements

**Session Persistence with Redis:**

```python
import redis.asyncio as redis
from google.adk.runners import Runner

# Redis client
redis_client = redis.from_url("redis://redis-service:6379")

@app.post("/v1/chat/stream")
async def chat_stream(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    
    # Retrieve session history
    history = await redis_client.get(f"session:{session_id}")
    
    async def event_generator():
        messages = []
        async for event in runner.run_live(request.message):
            if event.type == "text_chunk":
                messages.append(event.text)
                yield f"data: {event.text}\n\n"
        
        # Store session
        await redis_client.setex(
            f"session:{session_id}",
            3600,  # 1 hour TTL
            json.dumps(messages)
        )
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Cloud Logging Integration:**

```python
from google.cloud import logging as cloud_logging

# Initialize Cloud Logging
logging_client = cloud_logging.Client()
logging_client.setup_logging()

logger = logging.getLogger(__name__)

@app.post("/v1/chat/stream")
async def chat_stream(request: ChatRequest):
    logger.info(
        "Chat request received",
        extra={
            "session_id": request.session_id,
            "message_length": len(request.message)
        }
    )
    # ... rest of implementation
```

**Prometheus Metrics:**

```python
from prometheus_client import Counter, Histogram, generate_latest
from fastapi import Response

# Metrics
REQUEST_COUNT = Counter("adk_requests_total", "Total chat requests")
REQUEST_DURATION = Histogram("adk_request_duration_seconds", "Request duration")

@app.post("/v1/chat/stream")
@REQUEST_DURATION.time()
async def chat_stream(request: ChatRequest):
    REQUEST_COUNT.inc()
    # ... implementation

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

---

## Why Method 3 Wins: Summary

**Method 1 and Method 2 cannot achieve these requirements.** They are excellent for local testing but fundamentally incompatible with containerized, scalable, production deployments.

---

## Final Architecture Diagram Reference

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Layer                              │
│  (Web App, Mobile App, CLI)                                 │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTPS
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              GKE Ingress (GCE Load Balancer)                │
│  • SSL Termination (Google-managed cert)                    │
│  • Global static IP                                         │
│  • Path-based routing                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Kubernetes Service (ClusterIP)                 │
│  • Load balances across pods                                │
│  • Port 80 → 8080                                           │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┼───────────┐
         ▼           ▼           ▼
    ┌────────┐  ┌────────┐  ┌────────┐
    │ Pod 1  │  │ Pod 2  │  │ Pod 3  │  ... (HPA scales 3-20)
    │────────│  │────────│  │────────│
    │FastAPI │  │FastAPI │  │FastAPI │
    │  +     │  │  +     │  │  +     │
    │Runner  │  │Runner  │  │Runner  │
    │run_live│  │run_live│  │run_live│
    └────┬───┘  └────┬───┘  └────┬───┘
         │           │           │
         └───────────┼───────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
    ┌─────────┐           ┌──────────────┐
    │ Redis   │           │ Cloud SQL    │
    │ (Cache) │           │ (Sessions)   │
    └─────────┘           └──────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│     Observability Stack                 │
│  • Cloud Logging (structured logs)      │
│  • Cloud Monitoring (metrics/alerts)    │
│  • Cloud Trace (request tracing)        │
│  • Prometheus (custom metrics)          │
└─────────────────────────────────────────┘
```

**You now have a complete, production-ready GKE architecture using Method 3 (Programmatic Runner) with SSE streaming support, horizontal autoscaling, and a clean development-to-production workflow.**
