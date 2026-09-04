# Framework Comparison Guide

Comparing FastAPI with Flask and Django for building RESTful APIs.

## Overview

This document provides a comprehensive comparison of FastAPI, Flask, and Django for API development, using this sample project as a reference for FastAPI implementation.

---

## 1. Setup Complexity

### FastAPI
**Difficulty: Low-Medium**

```bash
# Installation
pip install fastapi uvicorn sqlalchemy alembic

# Run
uvicorn app.main:app --reload
```

**Pros:**
- Modern, straightforward setup
- Built-in OpenAPI documentation
- Async support out of the box

**Cons:**
- Requires understanding of async/await
- More dependencies for full stack

---

### Flask
**Difficulty: Low**

```bash
# Installation
pip install flask flask-sqlalchemy flask-migrate

# Run
flask run
```

**Pros:**
- Minimal setup, very simple
- Large ecosystem of extensions
- Easy to understand for beginners

**Cons:**
- Requires manual API documentation setup
- No built-in validation
- Async support requires additional setup

---

### Django (with Django REST Framework)
**Difficulty: Medium-High**

```bash
# Installation
pip install django djangorestframework

# Setup
django-admin startproject myproject
python manage.py startapp myapp
python manage.py migrate
```

**Pros:**
- Batteries-included approach
- Built-in admin panel
- Strong ORM

**Cons:**
- Heavy framework for simple APIs
- Steeper learning curve
- More configuration required

---

## 2. Code Structure & Organization

### FastAPI (This Project)

```
app/
├── api/routes/      # Route handlers
├── core/            # Config, security
├── models/          # Database models
├── schemas/         # Pydantic schemas
├── services/        # Business logic
└── main.py          # Application entry
```

**Characteristics:**
- Clear separation of concerns
- Type-driven development
- Explicit dependencies

---

### Flask

```
app/
├── routes/          # Route handlers
├── models/          # Database models
├── forms/           # WTForms (validation)
├── services/        # Business logic
└── __init__.py      # Application factory
```

**Characteristics:**
- Flexible structure
- Blueprint-based organization
- Manual schema management

---

### Django REST Framework

```
myapp/
├── models.py        # Database models
├── serializers.py   # DRF serializers
├── views.py         # ViewSets/Views
├── urls.py          # URL routing
└── admin.py         # Admin configuration
```

**Characteristics:**
- Convention over configuration
- Model-centric approach
- Class-based views

---

## 3. Type Safety & Validation

### FastAPI ⭐⭐⭐⭐⭐

```python
from pydantic import BaseModel, Field

class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    price: float = Field(gt=0)
    stock: int = Field(ge=0)
```

- Built-in Pydantic validation
- Automatic OpenAPI schema generation
- Type hints throughout
- Editor autocomplete

---

### Flask ⭐⭐⭐

```python
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField
from wtforms.validators import DataRequired, NumberRange

class ProductForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    price = FloatField('Price', validators=[NumberRange(min=0)])
```

- Requires WTForms or Marshmallow
- Manual schema management
- Less type safety

---

### Django REST Framework ⭐⭐⭐⭐

```python
from rest_framework import serializers

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['name', 'price', 'stock']
    
    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be positive")
        return value
```

- Serializers provide validation
- Model-based approach
- Good validation but verbose

---

## 4. Documentation

### FastAPI ⭐⭐⭐⭐⭐

- **Auto-generated**: Swagger UI, ReDoc
- **Interactive**: Test APIs in browser
- **Always in sync**: Generated from code

```python
@router.post("/products", summary="Create product")
async def create_product(product: ProductCreate):
    """
    Create a new product with:
    - **name**: Product name
    - **price**: Price (must be positive)
    """
    pass
```

---

### Flask ⭐⭐

- **Manual**: Requires flask-swagger, flasgger
- **Not automatic**: Need to maintain separately
- **Extra work**: Documentation can drift from code

---

### Django REST Framework ⭐⭐⭐⭐

- **Semi-automatic**: Browsable API
- **CoreAPI**: Schema generation available
- **Good but not as polished** as FastAPI

---

## 5. Testing

### FastAPI

```python
from httpx import AsyncClient

async def test_create_product(client: AsyncClient):
    response = await client.post(
        "/v1/products",
        json={"name": "Test", "price": 99.99, "stock": 10}
    )
    assert response.status_code == 201
```

- Use pytest with httpx
- Async test support
- Dependency injection makes mocking easy

---

### Flask

```python
def test_create_product(client):
    response = client.post(
        '/api/products',
        json={"name": "Test", "price": 99.99, "stock": 10}
    )
    assert response.status_code == 201
```

- Use pytest or unittest
- Simple test client
- Straightforward mocking

---

### Django

```python
from rest_framework.test import APIClient

def test_create_product():
    client = APIClient()
    response = client.post(
        '/api/products/',
        {"name": "Test", "price": 99.99, "stock": 10}
    )
    assert response.status_code == 201
```

- Built-in testing framework
- Fixtures and factories
- Database rollback per test

---
