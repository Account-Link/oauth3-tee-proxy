// Base64URL decoder helper
function base64urlDecode(input) {
    // Convert base64url to base64
    input = input.replace(/-/g, '+').replace(/_/g, '/');
    // Add padding if needed
    const pad = input.length % 4;
    if (pad) {
        input += '='.repeat(4 - pad);
    }
    return atob(input);
}

// Common error handling
function handleWebAuthnError(error) {
    console.error('WebAuthn error:', error);
    alert('Operation failed: ' + error.message);
} 