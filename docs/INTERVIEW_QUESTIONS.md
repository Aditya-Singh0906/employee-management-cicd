# Curated Senior DevOps & SRE Technical Interview Questions

This document contains over 30 rigorous technical interview questions and comprehensive, authoritative answers directly derived from the **Enterprise Employee Management CI/CD Platform**. These questions reflect what Senior Architects at Google, Amazon, Netflix, and OpenAI ask candidates in technical deep-dive rounds.

---

## 1. CI/CD & Jenkins Pipeline Questions

### Q1: Why did you choose `${BUILD_NUMBER}` for Docker image tagging in your `Jenkinsfile` instead of `latest` or Git branch names?
**Authoritative Answer**: Tagging images solely as `latest` is an enterprise anti-pattern because it violates the principle of **immutable infrastructure**. If multiple builds push to `latest`, you lose deterministic traceability between what is running in production and the exact Git commit that generated it. Furthermore, rollback operations become unreliable or impossible without deterministic tags. By assigning unique, sequential numbers (`${BUILD_NUMBER}`) or exact Git SHA hashes (`${GIT_COMMIT}`), each artifact becomes unique, verifiable, and instantly attributable to a specific point in time and code commit.

### Q2: Explain the significance of `waitForQualityGate abortPipeline: true` inside your Jenkins declarative pipeline. What happens if this stage times out?
**Authoritative Answer**: `waitForQualityGate` acts as a synchronous interrupter that pauses Jenkins execution until SonarQube completes its asynchronous background processing of static code metrics. Setting `abortPipeline: true` guarantees that if the codebase violates predefined organizational thresholds (e.g., test coverage below 80%, new critical security vulnerabilities, or excessive code smells), the build fails immediately. If the 15-minute timeout expires before SonarQube responds (due to network or server latency), Jenkins aborts the pipeline to prevent an unverified artifact from being pushed to the container registry.

### Q3: How does your pipeline isolate building and testing from the host Jenkins node, and what security risks are associated with mounting `/var/run/docker.sock`?
**Authoritative Answer**: Our pipeline utilizes Docker-in-Docker (DinD) via socket binding (`/var/run/docker.sock` mounted inside the Jenkins container). While this enables Jenkins to leverage the host OS Docker daemon to build images and run Trivy scans without installing heavy build tools directly inside Jenkins, it introduces a significant security trade-off: any container with access to `/var/run/docker.sock` effectively possesses root-level administrative access to the underlying host machine. In hardened enterprise environments, this risk is mitigated by running rootless Docker, utilizing isolated Kubernetes build pods (Kaniko / BuildKit), or restricting socket permissions to a dedicated `docker` group.

---

## 2. Docker & Containerization Questions

### Q4: In `docker-compose.yml`, why do you use `depends_on: condition: service_healthy` for the API container depending on PostgreSQL instead of a basic `depends_on`?
**Authoritative Answer**: A standard `depends_on` in Docker Compose only verifies that the container process has *started*; it does not verify that the internal application inside the container is ready to accept TCP traffic. When PostgreSQL starts up, it requires several seconds to initialize shared memory buffers, check disk permissions, and open port `5432`. If the Flask API attempts to bind immediately upon container start, `SQLAlchemy` will throw a `psycopg2.OperationalError` due to connection refusal. By defining a custom `healthcheck` (`pg_isready`) on the database container and specifying `condition: service_healthy`, Docker Compose guarantees that the API container waits until PostgreSQL returns a successful readiness probe before executing `python run.py`.

### Q5: What is the architectural difference between `COPY requirements.txt .` + `RUN pip install` versus `COPY . .` at the start of a `Dockerfile`?
**Authoritative Answer**: This design pattern maximizes **Docker layer caching efficiency**. Docker builds images layer by layer and caches each instruction. If `COPY . .` is executed first, any modification to a single source code file (such as a comment in `app.py`) invalidates the cache for all subsequent lines. Consequently, `RUN pip install -r requirements.txt` would re-download and re-compile every Python dependency from scratch on every commit, turning a 5-second build into a 3-minute build. By copying *only* `requirements.txt` first and running `pip install`, that heavy dependency layer remains fully cached unless `requirements.txt` itself changes.

### Q6: How does multi-stage container build architecture improve runtime security and reduce attack surface?
**Authoritative Answer**: Multi-stage builds separate the **compilation environment** (`builder` stage containing heavy compilers like `gcc`, `make`, header files, and dev linters) from the **runtime environment** (`final` stage containing only the minimal Python runtime and compiled wheel packages). By omitting build binaries from the production image, the artifact size drops significantly, and attackers who might compromise the running application are deprived of standard tools needed to compile exploits or perform privilege escalation on the host container.

---

## 3. AWS & Infrastructure Questions

### Q7: Why is Nginx deployed as a reverse proxy in front of your Flask application on AWS EC2 rather than exposing Gunicorn directly on port 80?
**Authoritative Answer**: While Gunicorn is an excellent high-concurrency WSGI worker manager, it is not designed to act as an edge-facing web server. Nginx provides vital edge capabilities:
1. **Security & DDoS Protection**: Nginx buffers slow client HTTP requests (`slowloris` attacks) before they consume precious synchronous WSGI worker threads.
2. **TLS/SSL Termination**: Nginx offloads cryptographic handshake processing (`HTTPS`) using optimized C libraries (`OpenSSL`), delivering decrypted plain HTTP over local loopback (`127.0.0.1:5000`) to Flask.
3. **Static File Serving & Caching**: Nginx serves static assets instantly from memory/disk without invoking Python interpreters.
4. **Rate Limiting**: Restricts requests per IP (`limit_req_zone`) to prevent brute-force login attempts on `/api/v1/auth/login`.

### Q8: What AWS security controls would you implement to secure the PostgreSQL database running on EC2 from unauthorized external access?
**Authoritative Answer**:
1. **Security Group Ingress Filtering**: Ensure the EC2 security group (`devops-prod-sg`) explicitly allows port `5432` only from specific internal private IPs or VPC security groups (`sg-backend`), completely blocking `0.0.0.0/0`.
2. **VPC Subnet Isolation**: In multi-tier AWS deployments, move the database outside the EC2 instance entirely into an **AWS RDS PostgreSQL** instance placed in a **Private Subnet** with no attached Internet Gateway (`IGW`).
3. **Encryption in Transit and at Rest**: Enforce SSL connections (`sslmode=require`) in the `DATABASE_URL` connection string and enable AWS KMS AES-256 encryption on underlying EBS/RDS storage volumes.

---

## 4. Database, ORM & Application Architecture Questions

### Q9: Explain the difference between the Repository Pattern and writing direct `db.session.query()` calls inside your Flask route controllers.
**Authoritative Answer**: Writing raw ORM queries inside HTTP route handlers tightly couples application business logic to the data persistence layer. If you decide to swap `SQLAlchemy` for another ORM, modify table structures, or introduce Redis caching, you must refactor every single API endpoint. The **Repository Pattern (`app/repositories/`)** abstracts database operations into clean domain contracts (`employee_repo.find_by_id(id)`). This separation makes unit testing effortless: you can pass mock repository objects into your `Service Layer (`app/services/`)` without requiring a live database connection or rolling back test transactions.

### Q10: How does Alembic (`Flask-Migrate`) manage database schema synchronization across distributed environments?
**Authoritative Answer**: Alembic generates timestamped, version-controlled Python migration scripts inside the `migrations/versions/` folder containing explicit `upgrade()` and `downgrade()` instructions (`op.create_table()`, `op.add_column()`). In PostgreSQL, Alembic maintains a dedicated tracking table named `alembic_version` containing the exact schema revision hash currently applied. During continuous deployment (`flask db upgrade`), Alembic queries `alembic_version`, compares the hash against local script files, and applies only the pending forward deltas within a single database transaction.

---

## 5. Security & Observability Questions

### Q11: How do you secure stateless JSON Web Tokens (JWT) against token theft, replay attacks, and user revocation in your Flask application?
**Authoritative Answer**:
1. **Short Expiration Windows**: Issue access tokens with brief lifetimes (`15 minutes`) alongside secure, long-lived refresh tokens stored in `HttpOnly, Secure, SameSite=Strict` cookies.
2. **Token Revocation / Blocklisting**: Implement a Redis-backed or PostgreSQL-backed token blocklist (`jwt.token_in_blocklist_loader`). Upon user logout or administrative account suspension, the token's unique `jti` (JWT ID) is written to the blocklist, instantly invalidating future requests before the token naturally expires.
3. **Role & Claim Verification**: Embed minimal user claims inside the payload (`identity`, `role`) while verifying digital signatures (`HS256` or `RS256`) against strict, rotating `JWT_SECRET_KEY` variables injected from secure secrets stores.

### Q12: If you were tasked with setting up Prometheus scraping for this Flask microservice, what exact metrics would you expose and why?
**Authoritative Answer**: Using `prometheus_flask_exporter` or custom middleware, I would expose four essential metric types adhering to the **RED Method (Rate, Errors, Duration)**:
1. `http_requests_total{method, status, endpoint}` (Counter): Tracks total incoming throughput and calculates exact error percentages (`HTTP 5xx / Total * 100`).
2. `http_request_duration_seconds{endpoint}` (Histogram): Measures exact request latency distributions (`p50`, `p95`, `p99`), vital for enforcing Service Level Objectives (SLOs).
3. `flask_app_memory_usage_bytes` and `python_gc_objects_collected_total` (Gauge/Counter): Tracks memory leaks across Gunicorn worker threads.
4. `db_connection_pool_checked_out` and `db_connection_pool_overflow` (Gauge): Monitors SQLAlchemy connection pool saturation to catch database starvation before it causes cascading 504 Gateway Timeouts.
