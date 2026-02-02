#!/bin/bash
API_BASE_URL="http://127.0.0.1:5000"
LOGIN_URL="$API_BASE_URL/auth/login"
API_URL="$API_BASE_URL/chatbot/" 

RESPONSE=$(curl -s -X POST "$LOGIN_URL" \
  -H "Content-Type: application/json" \
  -d '{"username": "Mathieu", "password": "Admin@1234"}')

echo "Raw login response:"
echo "$RESPONSE"
echo ""

if ! echo "$RESPONSE" | jq empty 2>/dev/null; then
    echo "Error: Response is not valid JSON"
    echo "Response received: $RESPONSE"
    exit 1
fi

TOKEN=$(echo "$RESPONSE" | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
    echo "Auth Failed - Token is null or empty"
    echo "Full response: $RESPONSE"
    exit 1
fi

echo "Authentication successful!"
echo "Token: ${TOKEN:0:20}..."
echo ""

do_test() {
    echo "=== $1 ==="
    curl -s -X POST "$API_URL" \
         -H "Authorization: Bearer $TOKEN" \
         -H "Content-Type: application/json" \
         -d "{\"message\": \"$2\"}" \
         -w "\n\n"
}

do_test "Test 1: Greeting" "Hello"
do_test "Test 2: Help Request" "Help"
do_test "Test 3: Product Search" "Find product aspirin"
do_test "Test 4: Client Search" "Search for client"
do_test "Test 5: Doctor Search" "Find doctor"
do_test "Test 6: Global Search" "John"
do_test "Test 7: Empty Message" ""
do_test "Test 8: Invalid Input" "Find email example@example.com"

LARGE_MSG=$(head -c 1000 < /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 100 | head -n 1)
do_test "Test 9: Large Input" "$LARGE_MSG"

do_test "Test 10: Special Characters" "!@#$%^&*()_+{}[]|:;<>?,./"
do_test "Test 11: Mixed Case" "fInD PrOdUcT AsPiRiN"
do_test "Test 12: Numeric" "12345"
do_test "Test 13: SQL Injection" "1; DROP TABLE users;"
do_test "Test 14: XSS Attempt" "<script>alert('XSS')</script>"
do_test "Test 15: Valid Product" "paracetamol 500mg"
do_test "Test 16: Valid Client" "search client"
do_test "Test 17: Valid Doctor" "find doctor"
do_test "Test 18: General Inquiry" "Find all products"

echo "=== All tests completed ==="