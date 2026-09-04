# FastAPI Sample Project

A FastAPI sample project demonstrating best practices for building RESTful APIs with Python. This project is designed for comparing FastAPI with other Python web frameworks like Flask and Django.

##  Features

- **RESTful API Design** - Complete CRUD operations for Products resource
- **JWT Authentication** - Secure user registration and login with JWT tokens
- **Async Database Operations** - SQLAlchemy 2.0 with async support and MySQL
- **Structured Logging** - Comprehensive logging with JSON and text formats
- **Contract-Driven Responses** - Resource responses, Problem Details errors, cursor pagination
- **Type Safety** - Full type hints and Pydantic validation
- **Auto-generated Documentation** - Interactive Swagger UI and ReDoc
- **Testing Suite** - Comprehensive tests with pytest and 70%+ coverage
- **Code Quality** - Black and isort for consistent code formatting
- **Database Migrations** - Alembic for managing database schema changes

##  Requirements

- Python 3.8+
- MySQL 5.7+ or MySQL 8.0+
- pip or virtualenv for dependency management

##  Technology Stack

| Component | Technology |
|-----------|-----------|
| **Web Framework** | FastAPI 0.109.0 |
| **Server** | Uvicorn (ASGI server) |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Database** | MySQL with aiomysql driver |
| **Authentication** | JWT (python-jose) |
| **Password Hashing** | Bcrypt (passlib) |
| **Validation** | Pydantic 2.0 |
| **Migrations** | Alembic |
| **Testing** | pytest with httpx |
| **Code Formatting** | Black + isort |

##  Project Structure

```
fastapi_sample/
├── app/
│   ├── api/
│   │   └── routes/          # API route handlers
│   │       ├── auth.py      # Authentication endpoints
│   │       ├── health.py    # Health check endpoints
│   │       └── products.py  # Product CRUD endpoints
│   ├── constants/
│   │   └── messages.py      # API messages and status constants
│   ├── core/
│   │   ├── config.py        # Application configuration
│   │   └── security.py      # Security utilities (JWT, hashing)
│   ├── db/
│   │   ├── base.py          # Database base configuration
│   │   └── session.py       # Database session management
│   ├── dependencies/
│   │   └── auth.py          # FastAPI dependencies (auth)
│   ├── middleware/          # Custom middleware
│   ├── models/
│   │   ├── base.py          # Base model with common fields
│   │   ├── user.py          # User model
│   │   └── product.py       # Product model
│   ├── schemas/
│   │   ├── problem.py       # Problem Details error schema
│   │   ├── user.py          # User schemas
│   │   └── product.py       # Product schemas
│   ├── services/
│   │   ├── auth_service.py  # Authentication business logic
│   │   └── product_service.py # Product business logic
│   ├── utils/
│   │   ├── logger.py        # Logging configuration
│   │   ├── problem.py       # Problem Details response helper
│   │   ├── cursor.py        # Cursor encode/decode helper
│   │   └── serialization.py # Resource serialization and ETag helper
│   └── main.py              # Application entry point
├── tests/
│   ├── conftest.py          # Pytest fixtures
│   ├── test_auth.py         # Authentication tests
│   ├── test_auth_service.py # Auth service tests
│   ├── test_health.py       # Health route tests
│   ├── test_products.py     # Product route tests
│   ├── test_product_service.py # Product service tests
│   └── test_security.py     # Security utility tests
├── alembic/
│   ├── versions/            # Migration files
│   └── env.py               # Alembic configuration
├── docs/
│   ├── API.md               # API documentation
│   ├── API_GOVERNANCE.md    # API ownership and lifecycle policy
│   └── COMPARISON.md        # Framework comparison guide
├── .env                     # Local environment variables (not committed)
├── alembic.ini              # Alembic configuration
├── pyproject.toml           # Project metadata and tool config
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

##  Getting Started

### 1. Clone the Repository

```bash
git clone <repository-url>
cd fastapi_sample
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file in the project root and set the following variables:

```env
# Database Configuration
DATABASE_URL=mysql+aiomysql://root:your_password@localhost:3306/fastapi_sample

# JWT Secret (generate a secure key)
SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32

# Other settings
ENVIRONMENT=development
DEBUG=True
```

### 5. Create Database

Create the MySQL database:

```bash
mysql -u root -p
CREATE DATABASE fastapi_sample;
CREATE DATABASE fastapi_sample_test;  # For testing
exit;
```

### 6. Run Database Migrations

```bash
alembic upgrade head
```

This will create the necessary tables (`users` and `products`) in your database.

### 7. Run the Application

```bash
uvicorn app.main:app --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

##  Testing

### Run All Tests

```bash
python3 -m pytest tests -v --cov=app --cov-report=term-missing --cov-report=html
```

### View Coverage Report

After running tests, open `htmlcov/index.html` in your browser to see the detailed coverage report.

### Run Specific Tests

```bash
# Test only authentication
pytest tests/test_auth.py -v

# Test only products
pytest tests/test_products.py -v
```

##  Code Formatting

Format all code with Black and isort:

```bash
python3 -m isort app tests
python3 -m black app tests
```

##  API Documentation

### Quick Start - Try the API

1. **Register a new user:**

```bash
curl -X POST "http://localhost:8000/v1/auth/register" \
  -H "Idempotency-Key: 7e62e9b6-4f67-45f9-b8be-4f4f9a06b173" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123"}'
```

2. **Login to get access token:**

```bash
curl -X POST "http://localhost:8000/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123"}'
```

3. **Create a product (requires authentication):**

```bash
curl -X POST "http://localhost:8000/v1/products" \
  -H "Idempotency-Key: e24f3381-6800-40e4-b6d2-f04193f0f3f3" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "name": "Laptop",
    "description": "High-performance laptop",
    "price": 999.99,
    "stock": 50
  }'
```

4. **List all products (public):**

```bash
curl "http://localhost:8000/v1/products?limit=10"
```

For complete API documentation, see [docs/API.md](docs/API.md) or visit the interactive documentation at http://localhost:8000/docs

##  Authentication

The API uses JWT (JSON Web Tokens) for authentication:

1. Register a new account at `/v1/auth/register` (with `Idempotency-Key` header)
2. Login at `/v1/auth/login` to receive an access token
3. Include the token in the Authorization header for protected endpoints:
   ```
   Authorization: Bearer <your_access_token>
   ```

### Protected vs Public Endpoints

**Public Endpoints** (no authentication required):
- `GET /v1/products` - List products (cursor pagination)
- `GET /v1/products/{product_id}` - Get single product (UUID id)
- `POST /v1/auth/register` - Register new user (requires `Idempotency-Key`)
- `POST /v1/auth/login` - Login

**Protected Endpoints** (requires authentication):
- `GET /v1/auth/me` - Get current user info
- `POST /v1/products` - Create product (requires `Idempotency-Key`)
- `PATCH /v1/products/{product_id}` - Partial update product (requires `If-Match`)
- `DELETE /v1/products/{product_id}` - Delete product


##  Troubleshooting

### Database Connection Issues

If you encounter database connection errors:

1. Verify MySQL is running: `mysql -u root -p`
2. Check database exists: `SHOW DATABASES;`
3. Verify credentials in `.env` file
4. Ensure `aiomysql` is installed: `pip install aiomysql`

### Migration Issues

If Alembic migrations fail:

```bash
# Reset migrations ( This will drop all tables!)
alembic downgrade base
alembic upgrade head
```

### Import Errors

If you get import errors, ensure you're in the virtual environment:

```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---
