import base64

# Load the service account JSON
with open("service_account.json", "rb") as f:
    encoded = base64.b64encode(f.read()).decode("utf-8")

# Save to a file
with open("encoded.txt", "w") as out:
    out.write(encoded)

print("✅ Base64 encoding complete. Check encoded.txt.")
