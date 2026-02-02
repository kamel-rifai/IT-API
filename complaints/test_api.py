from fastapi import FastAPI
from fastapi.testclient import TestClient
import complaints.main as complaints_module

app = FastAPI()
app.include_router(complaints_module.router, prefix="/complaints")
client = TestClient(app)

payload = {
    "name": "Test complaint from API",
    "description": "This is a test complaint inserted by the test script.",
    "reporter_name": "QA",
    "reporter_email": "qa@example.com"
}

resp = client.post("/complaints/", json=payload)
print('POST Status:', resp.status_code)
print('POST JSON:', resp.json())

# List recent complaints
lresp = client.get('/complaints/')
print('LIST Status:', lresp.status_code)
print('LIST JSON sample count:', len(lresp.json()))

# Fetch the created complaint by id
created_id = resp.json().get('id')
if created_id:
    greq = client.get(f'/complaints/{created_id}')
    print('GET Status:', greq.status_code)
    print('GET JSON:', greq.json())
