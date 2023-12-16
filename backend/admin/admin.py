from fastapi import FastAPI, Request, HTTPException
from json import JSONDecodeError
import httpx
import uvicorn
import strawberry
from strawberry.asgi import GraphQL
from typing import Optional, List

### Set up the API URLs ###

feedback_base_url = 'http://3.145.189.61:6060/api'
feedback_endpoints = {
    'get': '/feedback/<id>',
    'get_all': '/admin/feedback',
    'get_all_feedback_only': '/admin/feedbackonly',
    'action': '/admin/feedback/<id>/action'
}

admin_base_url = f'{feedback_base_url}/admin'
admin_endpoints = {
    'get': '/<id>',
    'post': '',
    'put': '/<id>',
    'delete': '/<id>',
    'check': '/check',
    'action': '/<id>/action'
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

async def make_get_request_for_graphql(url: str):
    try:
        return await make_api_request("GET", url)
    except HTTPException as e:
        if e.status_code != 200:
            return None

async def make_get_graphql_query(url: str, query: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json={'query': query})
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()

### Define the GraphQL schema ###
@strawberry.type
class Admin:
    adminId: int
    email: str
    isDeleted: bool
    actions: 'Optional[List[Action]]' = strawberry.field(default_factory=list)

@strawberry.type
class Action:
    actionId: int
    adminId: int
    feedbackId: int
    comment: str
    actionDate: str
    admin: Optional[Admin] = None
    feedback: 'Optional[Feedback]' = None

@strawberry.type
class Feedback:
    feedbackId: int
    name: Optional[str]
    email: Optional[str]
    text: str
    submissionDate: str
    isDeleted: bool
    actions: List[Action] = strawberry.field(default_factory=list)

async def fetch_admin(admin_id: int) -> Admin:
    url = API_URLS['admin']['get'].replace('<id>', str(admin_id))
    data = await make_get_request_for_graphql(url)
    return Admin(**data) if data else None

async def fetch_action(action_id: int) -> Action:
    url = API_URLS['action']['get'].replace('<id>', str(action_id))
    data = await make_get_request_for_graphql(url)
    return Action(**data) if data else None

async def fetch_feedback(id: int) -> Feedback:
    url = API_URLS['feedback']['get'].replace('<id>', str(id))
    data = await make_get_request_for_graphql(url)
    return Feedback(**data) if data else None

async def fetch_all_feedback() -> List[Feedback]:
    url = API_URLS['feedback']['get_all_feedback_only']
    data = await make_get_request_for_graphql(url)
    return [Feedback(**feedback_data) for feedback_data in data]

async def feedback_actions(self, info, feedback_id: int) -> List[Action]:
    url = API_URLS['feedback']['action'].replace('<id>', str(feedback_id))
    data = await make_api_request("GET", url)
    actions = [Action(**action_data) for action_data in data]
    for action in actions:
        action.admin = await fetch_admin(action.adminId)
    return actions

async def admin_actions(self, info, admin_id: int) -> List[Action]:
    url = API_URLS['admin']['action'].replace('<id>', str(admin_id))
    data = await make_api_request("GET", url)
    actions = [Action(**action_data) for action_data in data]
    for action in actions:
        action.feedback = await fetch_feedback(action.feedbackId)
    return actions

@strawberry.type
class Query:
    @strawberry.field()
    async def feedback(self, info, id: int) -> Optional[Feedback]:
        feedback = await fetch_feedback(id)
        if feedback:
            feedback.actions = await feedback_actions(self, info, id)
        return feedback

    @strawberry.field()
    async def action(self, info, id: int) -> Optional[Action]:
        action = await fetch_action(id)
        if action:
            action.admin = await fetch_admin(action.adminId)
            action.feedback = await fetch_feedback(action.feedbackId)
        return action

    @strawberry.field()
    async def admin(self, info, id: int) -> Optional[Admin]:
        admin = await fetch_admin(id)
        if admin:
            admin.actions = await admin_actions(self, info, id)
        return admin

    @strawberry.field()
    async def allFeedback(self, info) -> List[Feedback]:
        feedbacks = await fetch_all_feedback()
        for feedback in feedbacks:
            feedback.actions = await feedback_actions(self, info, feedback.feedbackId)
            for action in feedback.actions:
                action.admin = await fetch_admin(action.adminId)
        return feedbacks

schema = strawberry.Schema(query=Query)

graphql_app = GraphQL(schema)

### Set up the FastAPI app ###

app = FastAPI()
app.add_route("/graphql", graphql_app)

### Feedback resource available to admin ###

@app.get('/api/admin/feedback/')
async def get_all_feedback():
    return await make_api_request("GET", API_URLS['feedback']['get_all'])

@app.get('/api/admin/feedback')
async def get_feedback_without_slash():
    return await get_all_feedback()

@app.get('/api/admin/feedback/graphql')
async def get_all_feedback_graphql():
    query = """
    {
        allFeedback {
            feedbackId
            name
            email
            text
            submissionDate
            actions {
                actionId
                comment
                actionDate
                admin {
                    adminId
                    email
                    isDeleted
                }
            }
        }
    }
    """
    url = "http://localhost:6061/graphql"
    response = await make_api_request("POST", url, data={'query': query})
    return response

@app.get('/api/admin/feedback/{id}')
async def get_feedback(id: int):
    return await make_api_request("GET", API_URLS['feedback']['get'].replace('<id>', str(id)))

@app.get('/api/admin/feedback/{id}/actions')
async def get_feedback_actions(id: int):
    return await make_api_request("GET", API_URLS['feedback']['actions'].replace('<id>', str(id)))

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

@app.get('/api/admin/action')
async def get_all_action_without_slash():
    return await get_all_action()

# Not really to be consumed by the frontend, but here for completeness
@app.get('/api/admin/action/{id}')
async def get_action(id: int):
    return await make_api_request("GET", API_URLS['action']['get'].replace('<id>', str(id)))

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

if __name__ == "__main__":
    uvicorn.run("admin:app", host="0.0.0.0", port=6061, reload=True, log_level="debug")