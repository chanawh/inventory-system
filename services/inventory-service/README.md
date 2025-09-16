# Inventory Service

A simple FastAPI-based microservice for tracking inventory by SKU and location.

## Endpoints

- `GET /inventory/{sku}`  
  Returns a mapping of location to quantity for a given SKU.

- `POST /inventory/{sku}/adjust`  
  Adjusts inventory for a given SKU at a specific location.  
  Body:
  ```json
  {
    "sku": "ABC123",
    "location": "store1",
    "quantity": 10
  }
  ```

## How to Start and Run Locally

### Prerequisites

- Python 3.8+
- [pip](https://pip.pypa.io/en/stable/)
- (Optional) [Docker](https://docs.docker.com/get-docker/)

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd inventory-service
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Service

```bash
uvicorn src.main:app --reload
```

- The API will be available at: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 4. Running Tests

```bash
pytest
```

---

## Running with Docker

1. **Build the Docker image:**

   ```bash
   docker build -t inventory-service .
   ```

2. **Run the container:**
   ```bash
   docker run -p 8000:8000 inventory-service
   ```

---

## Notes

- Uses SQLite for simplicity.
- Add your event publishing logic where marked.
- Extend as needed for production use.
