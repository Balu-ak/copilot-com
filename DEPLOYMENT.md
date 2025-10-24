# AutoBrain Deployment Guide

Complete guide for deploying AutoBrain in various environments, from local development to production Kubernetes.

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Compose Production](#docker-compose-production)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Cloud Provider Setup](#cloud-provider-setup)
5. [CI/CD Pipeline](#cicd-pipeline)
6. [Monitoring & Observability](#monitoring--observability)
7. [Security Considerations](#security-considerations)

---

## 1. Local Development

### Prerequisites

- Docker Desktop 4.0+
- Docker Compose 2.0+
- Git
- Text editor

### Step-by-Step Setup

#### Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/autobrain.git
cd autobrain
```

#### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your favorite editor
nano .env  # or vim, code, etc.
```

**Minimum Required Configuration:**

```bash
# LLM Provider (choose one)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here

# Or use Anthropic
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=your-key-here
```

#### Step 3: Start Services

```bash
# Start all services in detached mode
docker-compose up -d

# Wait for services to be healthy (~30 seconds)
docker-compose ps
```

Expected output:
```
NAME                   STATUS              PORTS
autobrain-postgres     Up (healthy)        5432/tcp
autobrain-redis        Up (healthy)        6379/tcp
autobrain-weaviate     Up (healthy)        8080/tcp
autobrain-api          Up                  0.0.0.0:8000->8000/tcp
autobrain-web          Up                  0.0.0.0:3000->3000/tcp
```

#### Step 4: Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# Check API docs
open http://localhost:8000/docs

# Open frontend
open http://localhost:3000
```

#### Step 5: Test the Application

1. Open http://localhost:3000 in your browser
2. You should see the AutoBrain chat interface
3. Try a test query: "What is AutoBrain?"
4. You should receive a response from the AI

### Troubleshooting Local Setup

**Issue: Services won't start**

```bash
# Check Docker daemon is running
docker info

# Check for port conflicts
lsof -i :3000  # Check if port 3000 is in use
lsof -i :8000  # Check if port 8000 is in use

# View detailed logs
docker-compose logs -f api
```

**Issue: API can't connect to database**

```bash
# Restart PostgreSQL
docker-compose restart postgres

# Check database logs
docker-compose logs postgres

# Verify database is accessible
docker-compose exec postgres psql -U autobrain -d autobrain -c "SELECT 1;"
```

**Issue: Frontend can't reach API**

Check that `NEXT_PUBLIC_API_URL` in `.env` is set to `http://localhost:8000`

---

## 2. Docker Compose Production

For small-to-medium deployments on a single server.

### Prerequisites

- Ubuntu 22.04 LTS or similar
- 4+ CPU cores
- 16GB+ RAM
- Docker & Docker Compose installed
- Domain name configured

### Step-by-Step Deployment

#### Step 1: Prepare Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

#### Step 2: Clone and Configure

```bash
# Clone repository
git clone https://github.com/your-org/autobrain.git
cd autobrain

# Create production environment
cp .env.example .env
nano .env
```

**Production Environment Configuration:**

```bash
# API
API_SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=postgresql://autobrain:STRONG_PASSWORD_HERE@postgres:5432/autobrain
REDIS_URL=redis://redis:6379/0

# LLM
LLM_PROVIDER=openai
OPENAI_API_KEY=your_production_key

# Vector DB
WEAVIATE_URL=http://weaviate:8080

# Frontend
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

#### Step 3: Setup SSL/TLS (with Nginx)

Create `nginx.conf`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

server {
    listen 80;
    server_name api.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Setup Let's Encrypt:

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificates
sudo certbot --nginx -d yourdomain.com -d api.yourdomain.com
```

#### Step 4: Start Production Services

```bash
# Start services
docker-compose -f docker-compose.yml up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

#### Step 5: Setup Monitoring

```bash
# Create monitoring stack
cat > docker-compose.monitoring.yml <<EOF
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

volumes:
  prometheus_data:
  grafana_data:
EOF

# Start monitoring
docker-compose -f docker-compose.monitoring.yml up -d
```

#### Step 6: Setup Backups

```bash
# Create backup script
cat > backup.sh <<'EOF'
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup PostgreSQL
docker-compose exec -T postgres pg_dump -U autobrain autobrain > \
  $BACKUP_DIR/db_$DATE.sql

# Backup Weaviate
docker-compose exec -T weaviate backup create --backend filesystem --id $DATE

# Compress and rotate (keep 7 days)
gzip $BACKUP_DIR/db_$DATE.sql
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
EOF

chmod +x backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add line:
# 0 2 * * * /path/to/autobrain/backup.sh
```

---

## 3. Kubernetes Deployment

For production-grade, scalable deployments.

### Prerequisites

- Kubernetes cluster (1.25+)
- kubectl configured
- Helm 3+
- Container registry access

### Step-by-Step K8s Deployment

#### Step 1: Build and Push Images

```bash
# Login to container registry
docker login ghcr.io

# Build images
docker build -f infra/docker/Dockerfile.api -t ghcr.io/your-org/autobrain-api:latest .
docker build -f infra/docker/Dockerfile.web -t ghcr.io/your-org/autobrain-web:latest .

# Push images
docker push ghcr.io/your-org/autobrain-api:latest
docker push ghcr.io/your-org/autobrain-web:latest
```

#### Step 2: Create Namespace

```bash
kubectl create namespace autobrain
```

#### Step 3: Create Secrets

```bash
# Create secret from env file
kubectl create secret generic autobrain-secrets \
  --from-literal=OPENAI_API_KEY=your_key \
  --from-literal=DATABASE_URL=postgresql://... \
  --from-literal=API_SECRET_KEY=$(openssl rand -hex 32) \
  --namespace autobrain
```

#### Step 4: Deploy PostgreSQL

```yaml
# postgres-deployment.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: autobrain
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: autobrain
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        env:
        - name: POSTGRES_DB
          value: autobrain
        - name: POSTGRES_USER
          value: autobrain
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: autobrain-secrets
              key: POSTGRES_PASSWORD
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: autobrain
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
```

Apply:
```bash
kubectl apply -f postgres-deployment.yaml
```

#### Step 5: Deploy API

```yaml
# api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: autobrain-api
  namespace: autobrain
spec:
  replicas: 3
  selector:
    matchLabels:
      app: autobrain-api
  template:
    metadata:
      labels:
        app: autobrain-api
    spec:
      containers:
      - name: api
        image: ghcr.io/your-org/autobrain-api:latest
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: autobrain-secrets
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 2Gi
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 20
---
apiVersion: v1
kind: Service
metadata:
  name: autobrain-api
  namespace: autobrain
spec:
  selector:
    app: autobrain-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

Apply:
```bash
kubectl apply -f api-deployment.yaml
```

#### Step 6: Deploy Frontend

```yaml
# web-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: autobrain-web
  namespace: autobrain
spec:
  replicas: 2
  selector:
    matchLabels:
      app: autobrain-web
  template:
    metadata:
      labels:
        app: autobrain-web
    spec:
      containers:
      - name: web
        image: ghcr.io/your-org/autobrain-web:latest
        ports:
        - containerPort: 3000
        env:
        - name: NEXT_PUBLIC_API_URL
          value: "https://api.yourdomain.com"
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
---
apiVersion: v1
kind: Service
metadata:
  name: autobrain-web
  namespace: autobrain
spec:
  selector:
    app: autobrain-web
  ports:
  - port: 80
    targetPort: 3000
  type: ClusterIP
```

Apply:
```bash
kubectl apply -f web-deployment.yaml
```

#### Step 7: Setup Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: autobrain-ingress
  namespace: autobrain
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    kubernetes.io/ingress.class: nginx
spec:
  tls:
  - hosts:
    - yourdomain.com
    - api.yourdomain.com
    secretName: autobrain-tls
  rules:
  - host: yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: autobrain-web
            port:
              number: 80
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: autobrain-api
            port:
              number: 80
```

Apply:
```bash
kubectl apply -f ingress.yaml
```

#### Step 8: Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n autobrain

# Check services
kubectl get svc -n autobrain

# Check ingress
kubectl get ingress -n autobrain

# View logs
kubectl logs -f -l app=autobrain-api -n autobrain
```

---

## 4. Cloud Provider Setup

### AWS EKS

```bash
# Install eksctl
brew install eksctl  # macOS
# or download from https://eksctl.io

# Create cluster
eksctl create cluster \
  --name autobrain \
  --region us-east-1 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --managed

# Configure kubectl
aws eks update-kubeconfig --region us-east-1 --name autobrain

# Install AWS Load Balancer Controller
# Follow: https://docs.aws.amazon.com/eks/latest/userguide/aws-load-balancer-controller.html
```

### GCP GKE

```bash
# Create cluster
gcloud container clusters create autobrain \
  --region us-central1 \
  --num-nodes 3 \
  --machine-type n1-standard-2 \
  --enable-autoscaling \
  --min-nodes 1 \
  --max-nodes 5

# Get credentials
gcloud container clusters get-credentials autobrain --region us-central1
```

---

## 5. CI/CD Pipeline

### GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy AutoBrain

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push API
        run: |
          docker build -f infra/docker/Dockerfile.api \
            -t ghcr.io/${{ github.repository }}/api:${{ github.sha }} .
          docker push ghcr.io/${{ github.repository }}/api:${{ github.sha }}
      
      - name: Build and push Web
        run: |
          docker build -f infra/docker/Dockerfile.web \
            -t ghcr.io/${{ github.repository }}/web:${{ github.sha }} .
          docker push ghcr.io/${{ github.repository }}/web:${{ github.sha }}
      
      - name: Deploy to Kubernetes
        env:
          KUBE_CONFIG: ${{ secrets.KUBE_CONFIG }}
        run: |
          echo "$KUBE_CONFIG" | base64 -d > kubeconfig
          export KUBECONFIG=kubeconfig
          kubectl set image deployment/autobrain-api \
            api=ghcr.io/${{ github.repository }}/api:${{ github.sha }} \
            -n autobrain
          kubectl set image deployment/autobrain-web \
            web=ghcr.io/${{ github.repository }}/web:${{ github.sha }} \
            -n autobrain
```

---

## 6. Monitoring & Observability

### Prometheus + Grafana

```bash
# Install Prometheus Operator
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace

# Access Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
# Default: admin / prom-operator
```

### Application Metrics

Add to API:
```python
from prometheus_client import Counter, Histogram

requests_total = Counter('api_requests_total', 'Total API requests')
request_duration = Histogram('api_request_duration_seconds', 'Request duration')
```

---

## 7. Security Considerations

### Production Checklist

- [ ] Use strong, unique passwords for all services
- [ ] Enable HTTPS/TLS for all endpoints
- [ ] Configure network policies in Kubernetes
- [ ] Enable audit logging
- [ ] Rotate secrets regularly
- [ ] Use managed database services (RDS, Cloud SQL)
- [ ] Enable pod security policies
- [ ] Configure resource limits
- [ ] Enable auto-scaling
- [ ] Setup backup and disaster recovery
- [ ] Implement rate limiting
- [ ] Configure CORS properly
- [ ] Enable authentication (Clerk/Auth0/etc)
- [ ] Review and update dependencies regularly
- [ ] Setup security scanning (Snyk, Trivy)

---

## Need Help?

- Review logs: `docker-compose logs -f` or `kubectl logs -f pod/name`
- Check health endpoints: `/health` on API
- Verify environment variables are set correctly
- Ensure all required services are running
- Check network connectivity between services

For more help, open an issue on GitHub!
