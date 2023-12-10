from fastapi import FastAPI, Request, HTTPException
from json import JSONDecodeError
import httpx
import uvicorn
import strawberry
from strawberry.asgi import GraphQL
from datetime import datetime

### Set up the API URLs ###

admin_base_url = 'http://localhost:6060/api/admin'
admin_endpoints = {
    'get': '/<id>',
    'post': '',
    'put': '/<id>',
    'delete': '/<id>',
    'check': '/check'
}

feedback_base_url = 'http://localhost:6060/api/admin/feedback'
feedback_endpoints = {
    'get': '/<id>'
}

action_base_url = admin_base_url
action_endpoints = {
    'get': '/action/<id>',
    'post': '/<admin_id>/feedback/<feedback_id>',
    'put': '/action/<id>',
    'delete': '/action/<id>',
}

API_URLS = {
    'admin': {endpoint: admin_base_url + path for endpoint, path in admin_endpoints.items()},
    'feedback': {endpoint: feedback_base_url + path for endpoint, path in feedback_endpoints.items()},
    'action': {endpoint: action_base_url + path for endpoint, path in action_endpoints.items()}
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

### Define the GraphQL schema ###

@strawberry.type
class Feedback:
    id: int
    name: str
    email: str
    text: str
    submission_date: datetime
    isDeleted: int

@strawberry.type
class Action:
    id: int
    admin_id: int
    feedback_id: int
    comment: str
    action_date: datetime
    feedback: Feedback

@strawberry.type
class Query:
    @strawberry.field()
    async def feedback(self, info, id: int) -> Feedback:
        url = API_URLS['feedback']['get'].replace('<id>', str(id))
        return await make_api_request("GET", url)

    @strawberry.field()
    async def action(self, info, id: int) -> Action:
        url = API_URLS['action']['get'].replace('<id>', str(id))
        return await make_api_request("GET", url)

schema = strawberry.Schema(query=Query)

graphql_app = GraphQL(schema)

### Set up the FastAPI app ###

app = FastAPI()
app.add_route("/graphql", graphql_app)

### Admin resource ###

@app.post('/api/admin/')
async def post_admin(request: Request):
    data = await request.json()
    return await make_api_request("POST", API_URLS['admin']['post'], data)

# Not sure why, but no trailing slash here works for both w/ and w/o slash when calling
@app.post('/api/admin/check')   
async def check_admin_email(request: Request):
    data = await request.json()
    return await make_api_request("POST", API_URLS['admin']['check'], data)

@app.get('/api/admin/')
async def get_all_admin():
    return await make_api_request("GET", API_URLS['admin']['get'].replace('<id>', ''))

@app.get('/api/admin/{id}')
async def get_admin(id: int):
    return await make_api_request("GET", API_URLS['admin']['get'].replace('<id>', str(id)))

@app.put('/api/admin/{id}')
async def put_admin(id: int, request: Request):
    data = await request.json()
    return await make_api_request("PUT", API_URLS['admin']['put'].replace('<id>', str(id)), data)

@app.delete('/api/admin/{id}')
async def delete_admin(id: int):
    return await make_api_request("DELETE", API_URLS['admin']['delete'].replace('<id>', str(id)))

### Feedback resource available to admin ###

# TODO: Use graphQL to get all feedback with its actions and get feedback by id

### Action resource ###

@app.post('/api/admin/{admin_id}/feedback/{feedback_id}')
async def post_admin_action(admin_id: int, feedback_id: int, request: Request):
    data = await request.json()
    return await make_api_request("POST", API_URLS['action']['post'].replace('<admin_id>', str(admin_id)).replace('<feedback_id>', str(feedback_id)), data)

@app.put('/api/admin/action/{id}')
async def put_admin_action(id: int, request: Request):
    data = await request.json()
    return await make_api_request("PUT", API_URLS['action']['put'].replace('<id>', str(id)), data)

@app.delete('/api/admin/action/{id}')
async def delete_admin_action(id: int):
    return await make_api_request("DELETE", API_URLS['action']['delete'].replace('<id>', str(id)))

@app.get('/api/admin/action/')
async def get_all_action():
    return await make_api_request("GET", API_URLS['action']['get'].replace('<id>', ''))

# Not really to be consumed by the frontend, but here for completeness
@app.get('/api/admin/action/{id}')
async def get_action(id: int):
    return await make_api_request("GET", API_URLS['action']['get'].replace('<id>', str(id)))



if __name__ == "__main__":
    uvicorn.run("admin:app", host="0.0.0.0", port=6061, reload=True, log_level="debug")