# Part 1
1. Run the following commands:
(one terminal)
docker run -d --name mongo -p 27017:27017 mongo:7.0
(another terminal)
cd reports/hw06/backend
pip install -r requirements.txt
uvicorn app.main:app --port 8032 --reload
2. Open http://localhost:8032/docs to open swagger ui -> under vulnerability Docs (MongoDB)
GET /api/vul-docs
POST /api/vul-docs
{
    "title": "sgl vulnerability with login page",
    "description": "injection wwlerbility",
    "status": "open",
    "category": "injection",
    "discovered_at": "2026-10-18T22:55:24.566Z",
    "created_at": "2026-10-18T22:55:24.566Z",
    "updated_at": "2026-10-18T22:55:24.5662"
}
GET /api/vul-docs/{item_id}
item_id = same as item_id from result of the POST
PUT /api/vul-docs/{item_id}
item_id = same as item_id from result of the POST
{
    "title": "sg1 injection vulnerability update",
    "description": "injection vulnerability with login with new user",
    "status": "open",
    "category": "injection",
    "discovered_at": "2026-10-19T02:18:23.584Z"
}
DELETE /api/vul-docs/{item_id}
item_id = same as item_id from result of the POST

3. Open MongoDB Compass
View hw6 connection -> s0932_doc -> vulnerability_docs
# Part 2
1. Run the following commands:
(one terminal)
ollama pull qwen3:8b
ollama pull nomic-embed-text
(another terminal)
cd reports/hw06/backend
pip install -r requirements.txt
uvicorn app.main:app --port 8032 --reload
2. Open Postman to run 12 messages:
POST http://localhost:8032/api/chat
{
  "user_id": "test",
  "session_id": "s0932-demo-session",
  "message": ""
}

For the message put the following in order to replicate:
"Hi, my name is test and I manage security for a small bank"
"We mostly use Python and FastAPI for our internal tools"
"The login service is owned by the software team manager, Dolittle"
"Our patch deadline for critical vulnerabilities is 3 days"
"Every issue is tracked with a code like VUL-c321-2026-10-06"
"Please keep your answers short, I prefer bullet points answers"
"The biggest concern is the SQL injection in the login service for our bank"
"We are also checking problems from any new installations in the reports page"
"Our vendor for the reports page is Test Corp"
"Can you remind me what my name is and who owns the login service?"
"What is our deadline for critical issues?"
"Which vendor supplies the reports page?"
3. Open MongoDB Compass
View hw6 connection -> s0932_doc -> episodes, messages, summaries