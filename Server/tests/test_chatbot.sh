#!/bin/bash

API_URL="http://127.0.0.1:5000/chatbot/"

echo "=== Test 1: Greeting ==="
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}' \
  -w "\n\n"

echo "=== Test 2: Help Request ==="
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{"message": "Help"}' \
  -w "\n\n"

echo "=== Test 3: Product Search ==="
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{"message": "Find product aspirin"}' \
  -w "\n\n"

echo "=== Test 4: Client Search ==="
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{"message": "Search for client"}' \
  -w "\n\n"

echo "=== Test 5: Doctor Search ==="
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{"message": "Find doctor"}' \
  -w "\n\n"

echo "=== Test 6: Global Search ==="
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{"message": "John"}' \
  -w "\n\n"

echo "=== Test 7: Empty Message ==="
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{"message": ""}' \
  -w "\n\n"

echo "=== Test 8: Invalid Input ==="
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{"message": "Find email example@example.com"}'

echo "=== Test 9: Large Input ==="
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{"message": "'"$(head -c 10000 < /dev/urandom | tr -dc 'a-zA-Z0-9 ' | fold -w 100 | head -n 1)"'"}' \
  -w "\n\n"

echo "=== Test 10: Special Characters ==="
curl -s -X POST $API_URL \
     -H "Content-Type: application/json" \
     -d "{\"message\": \"!@#$%^&*()_+{}[]|:;<>?,./'\"}"
echo -e "\n"

echo "=== Test 11: Mixed Case Input ==="
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{"message": "fInD PrOdUcT AsPiRiN"}' \
  -w "\n\n" 

echo "=== Test 12: Numeric Input ==="
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{"message": "Find product 12345"}' \
  -w "\n\n"

echo "=== Test 13: SQL Injection Attempt ==="
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{"message": "Find product 1; DROP TABLE users;"}' \
  -w "\n\n"

echo "=== Test 14: Cross-Site Scripting Attempt ==="
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{"message": "<script>alert(\"XSS\")</script>"}' \
  -w "\n\n"

echo "=== Test 15: Valid Product Search ==="
curl -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{"message": "Find product paracetamol 500mg"}'

echo "=== Test 16: Valid Client Search ==="
curl -s -X POST $API_URL \
     -H "Content-Type: application/json" \
     -d '{"message": "search client"}'
echo -e "\n"

echo "=== Test 17: Valid Doctor Search ==="
curl -s -X POST $API_URL\
     -H "Content-Type: application/json" \
     -d '{"message": "find doctor"}'
echo -e "\n"


echo "=== Test 18: General Inquiry ==="
curl -v -X POST $API_URL \
  -H "Content-Type: application/json" \
  -d '{"message": "Find all products"}'

echo "=== All tests completed ==="