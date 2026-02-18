curl -s -X POST http://localhost:8000/orchestrator/stream-answer \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "123456",
    "request_id": "12345678",
    "question": "hi what is your expected salary "
  }'