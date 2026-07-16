# Enterprise Architecture Guide

## 1. Architectural Overview & Design Philosophy

The **Enterprise Employee Management CI/CD Platform** is engineered according to enterprise cloud-native design principles: **Separation of Concerns**, **High Availability (HA)**, **Zero-Trust Security Edge**, **Immutable Infrastructure**, and **Automated Quality Verification**.

In a production-tier architecture, the application logic is completely decoupled from the underlying storage and orchestration layers. The system is designed around a clean 3-tier model deployed in Docker containers and managed via CI/CD automation.

---

## 2. Comprehensive System Architecture Diagram

```mermaid
graph TB
    subgraph External Clients
        Web[Web Browser / Dashboard]
        API_Client[Postman / Mobile API Clients]
        Developer[DevOps / Software Engineer]
    end

    subgraph Edge & Security Layer - AWS Cloud Edge
        R53[AWS Route 53 DNS<br>A Record / CNAME]
        CF[AWS CloudFront CDN / WAF<br>DDOS & SQLi Protection]
    end

    subgraph Compute Infrastructure - AWS EC2 Instance / VPC Public Subnet
        subgraph Host Operating System - Ubuntu 24.04 LTS
            Nginx[Nginx Reverse Proxy<br>Port: 80 / 443 HTTPS<br>Rate Limiting & SSL Termination]
            
            subgraph Docker Runtime Environment - Bridge Network
                API_Container[Flask REST API Container<br>Gunicorn WSGI Server<br>Port: 5000]
                DB_Container[PostgreSQL 16 Container<br>Port: 5432]
            end
        end
        Host_Logs[Host Log Directory<br>/var/log/nginx & /app/logs]
    end

    subgraph Persistent Data Layer
        Docker_Volume[(Docker Named Volume<br>postgres_data)]
        S3_Backup[AWS S3 Bucket<br>Automated Daily Dump]
    end

    subgraph CI/CD Automation & Security Tooling - Docker Network devops
        GitHub[GitHub Repository<br>Main / Develop / Feature Branches]
        Jenkins[Jenkins Master CI Server<br>Port: 8080<br>Declarative Jenkinsfile]
        SonarQube[SonarQube Quality Gate<br>Port: 9000<br>Static Code & Security Analysis]
        Trivy[Aqua Trivy Scanner<br>CVE & Vulnerability Analysis]
        ECR[Docker Registry<br>Amazon ECR / Docker Hub]
    end

    subgraph Observability Layer - Future Target
        Prometheus[Prometheus Server<br>Scraping cAdvisor & Node Exporter]
        Grafana[Grafana Dashboards<br>Port: 3000]
    end

    Web & API_Client -->|HTTPS / REST API| R53
    R53 --> CF
    CF -->|TLS/SSL Request| Nginx
    Nginx -->|Proxy Pass http://127.0.0.1:5000| API_Container
    API_Container -->|SQLAlchemy TCP/5432| DB_Container
    DB_Container --- Docker_Volume
    Docker_Volume -.->|Cron Snapshot| S3_Backup

    Developer -->|Git Push / PR| GitHub
    GitHub -->|Webhook Trigger| Jenkins
    Jenkins -->|Source Checkout| GitHub
    Jenkins -->|Code Analysis| SonarQube
    Jenkins -->|Build & Scan Image| Trivy
    Jenkins -->|Push Artifact| ECR
    Jenkins -->|SSH Deploy Script| Nginx

    Prometheus -.->|Scrape Metrics| API_Container
    Prometheus -.->|Scrape System| DB_Container
    Grafana -->|Query Metrics| Prometheus
```

---

## 3. Layer-by-Layer Architectural Analysis

### 3.1 Edge & Network Security Layer
- **DNS (AWS Route 53)**: Routes external domain traffic (`api.company.internal`) with health-check-enabled failover routing policies.
- **Reverse Proxy (Nginx)**: Acts as the single entry point (`0.0.0.0:80/443`) into the compute environment. It handles TLS/SSL termination, HTTP-to-HTTPS redirection, request buffering, client payload size restriction (`client_max_body_size 10M`), and rate limiting to prevent denial-of-service attempts before hitting the WSGI layer.

### 3.2 Application & Compute Layer
- **WSGI Process Management**: The application inside the Docker container is executed using Gunicorn (Green Unicorn) or WSGI workers behind Flask. This prevents Flask’s built-in single-threaded development server (`run.py`) from buckling under concurrent production requests.
- **Application Structure**: Implements the **Repository Pattern** and **Service Layer Pattern**:
  - **Controllers/API Blueprints (`app/api/`)**: Handle HTTP request parsing, input validation via `Marshmallow`/`Pydantic` schemas, and HTTP status code formatting.
  - **Services (`app/services/`)**: Encapsulate pure business logic, transactional boundaries, and domain rules.
  - **Repositories (`app/repositories/`)**: Isolate database queries and ORM interactions (`SQLAlchemy`) so the domain model remains completely decoupled from raw database calls.
  - **Models (`app/models/`)**: Define declarative database entities and relationships (`Employee`, `User`).

### 3.3 Data & Persistence Layer
- **Relational Engine**: PostgreSQL 16 running inside an isolated Docker container or managed AWS RDS instance.
- **Volume Isolation**: Uses Docker named volumes (`postgres_data`) mapped directly to `/var/lib/postgresql/data` within the container. This guarantees that container restarts or upgrades do not result in data loss.
- **Schema Migrations**: Controlled entirely through **Alembic (`Flask-Migrate`)**. Database schemas (`alembic_version` tracking table) are strictly versioned, ensuring zero-downtime forward and backward compatibility across deployments.

### 3.4 Continuous Integration & Delivery (CI/CD) Layer
- **Isolation**: Jenkins and code quality tools execute on a dedicated Docker bridge network (`devops`), completely segmented from public-facing production containers.
- **Vulnerability Inspection**: Every container artifact produced (`employee-management-api:${BUILD_NUMBER}`) is scanned locally using **Aqua Security Trivy** against OS-level CVE databases and Python package vulnerabilities before pushing to the remote Docker registry (Amazon ECR / Docker Hub).

---

## 4. End-to-End Request Data Flow

Let us trace what happens when an authenticated client requests `GET /api/v1/employees/1`:

```mermaid
sequenceDiagram
    autonumber
    actor Client as Client / Browser
    participant Nginx as Nginx Reverse Proxy
    participant API as Flask API (Gunicorn)
    participant Auth as JWT Middleware
    participant Service as Employee Service
    participant Repo as Employee Repository
    participant DB as PostgreSQL Container

    Client->>Nginx: GET /api/v1/employees/1<br>Authorization: Bearer <JWT>
    Nginx->>API: Proxy Pass request over internal socket
    API->>Auth: @jwt_required() validation
    Auth->>Auth: Decode token & check expiration / revocation
    Auth-->>API: Token valid (User ID: 42, Role: Admin)
    API->>Service: get_employee_by_id(employee_id=1)
    Service->>Repo: find_by_id(1)
    Repo->>DB: SELECT * FROM employees WHERE id = 1;
    DB-->>Repo: Return Row (id: 1, name: "John Doe", department: "Engineering")
    Repo-->>Service: Return Employee ORM Model instance
    Service->>Service: Serialize ORM Model to JSON Schema
    Service-->>API: Return serialized dictionary payload
    API-->>Nginx: HTTP 200 OK Application/JSON
    Nginx-->>Client: HTTP 200 OK Response with CORS headers
```

---

## 5. Security Architecture & Threat Mitigation

1. **Least Privilege Principle**:
   - The Flask API container runs as a non-root user (`USER appuser`) defined in the multi-stage build.
   - Database user `postgres` restricts access strictly to the `employee_db` schema.
2. **Network Segmentation**:
   - Only `Nginx` exposes ports (`80/443`) to the external host/network.
   - Flask (`5000`) and PostgreSQL (`5432`) bind strictly to the private internal Docker bridge network (`docker-compose.yml`), making direct external port scans against the database impossible.
3. **Secret Management**:
   - No hardcoded secrets (`JWT_SECRET_KEY`, `POSTGRES_PASSWORD`) reside inside source code or image layers.
   - Secrets are injected dynamically at container startup via secure `.env` files or AWS Secrets Manager / Parameter Store integration.
