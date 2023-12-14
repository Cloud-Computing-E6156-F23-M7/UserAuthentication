from fastapi import FastAPI, Request, HTTPException
from json import JSONDecodeError
import httpx
import uvicorn

app = FastAPI()

### Set up the API URLs ###

feedback_base_url = 'http://localhost:6060/api/feedback'
feedback_endpoints = {
    'get': '/<id>',
    'post': '',
    'put': '/<id>',
    'delete': '/<id>'
}

API_URLS = {
    'feedback': {endpoint: feedback_base_url + path for endpoint, path in feedback_endpoints.items()},
}

async def make_api_request(method: str, url: str, data=None):
    async with httpx.AsyncClient() as client:
        if method not in ["GET", "POST", "PUT", "DELETE"]:
            raise HTTPException(status_code=400, detail="Invalid method")

        if method in ["POST", "PUT"]:
            response = await getattr(client, method.lower())(url, json=data, follow_redirects=True)
        else:
            response = await getattr(client, method.lower())(url, follow_redirects=True)

        if response.status_code != 200 and response.status_code != 201:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        try:
            return response.json()
        except JSONDecodeError:
            return response.text

@app.post('/api/feedback/')
async def post_feedback(request: Request):
    data = await request.json()
    return await make_api_request("POST", API_URLS['feedback']['post'], data)

### Below should not be consumed unless we want to allow users to edit their feedback ###

@app.get('/api/feedback/{id}')
async def get_feedback(id: int):
    return await make_api_request("GET", API_URLS['feedback']['get'].replace('<id>', str(id)))

@app.put('/api/feedback/{id}')
async def put_feedback(id: int, request: Request):
    data = await request.json()
    return await make_api_request("PUT", API_URLS['feedback']['put'].replace('<id>', str(id)), data)

@app.delete('/api/feedback/{id}')
async def delete_feedback(id: int):
    return await make_api_request("DELETE", API_URLS['feedback']['delete'].replace('<id>', str(id)))

if __name__ == "__main__":
    uvicorn.run("feedback:app", host="0.0.0.0", port=6062, reload=True, log_level="debug")
    