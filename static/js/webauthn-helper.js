/**
 * WebAuthn Helper Functions
 * ========================
 * 
 * This file contains helper functions for WebAuthn/passkey operations,
 * providing common utilities for encoding/decoding, creating credentials,
 * and authenticating with credentials.
 */

/**
 * Convert base64url to ArrayBuffer
 * @param {string} base64url - Base64URL encoded string
 * @returns {ArrayBuffer} - Decoded ArrayBuffer
 */
function base64urlToArrayBuffer(base64url) {
  // Safety check to prevent errors with undefined values
  if (!base64url) {
    console.error("base64urlToArrayBuffer received undefined or null input");
    return new ArrayBuffer(0);
  }
  
  try {
    const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
    const padLen = (4 - (base64.length % 4)) % 4;
    const padded = base64 + '='.repeat(padLen);
    const binary = atob(padded);
    const buffer = new ArrayBuffer(binary.length);
    const bytes = new Uint8Array(buffer);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return buffer;
  } catch (error) {
    console.error("Error in base64urlToArrayBuffer:", error, "for input:", base64url);
    return new ArrayBuffer(0);
  }
}

/**
 * Convert ArrayBuffer to base64url
 * @param {ArrayBuffer} buffer - ArrayBuffer to encode
 * @returns {string} - Base64URL encoded string
 */
function arrayBufferToBase64url(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  const base64 = btoa(binary);
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

/**
 * Prepare WebAuthn registration options for the browser
 * @param {Object} options - Registration options from server
 * @returns {Object} - Prepared options with ArrayBuffers
 */
function prepareRegistrationOptions(options) {
  // Convert challenge to ArrayBuffer
  options.challenge = base64urlToArrayBuffer(options.challenge);
  
  // Convert user ID to ArrayBuffer if present
  if (options.user && options.user.id) {
    options.user.id = base64urlToArrayBuffer(options.user.id);
  }
  
  // Convert excluded credentials if present
  if (options.excludeCredentials) {
    options.excludeCredentials = options.excludeCredentials.map(cred => {
      return {
        ...cred,
        id: base64urlToArrayBuffer(cred.id)
      };
    });
  }
  
  return options;
}

/**
 * Prepare WebAuthn authentication options for the browser
 * @param {Object} options - Authentication options from server
 * @returns {Object} - Prepared options with ArrayBuffers
 */
function prepareAuthenticationOptions(options) {
  // Log the options for debugging
  console.log("Preparing authentication options:", typeof options);
  
  // Handle string input (parse if needed)
  let parsedOptions = options;
  if (typeof options === 'string') {
    try {
      console.log("Parsing options string");
      parsedOptions = JSON.parse(options);
    } catch (e) {
      console.error("Failed to parse options string:", e);
      throw new Error("Failed to parse authentication options");
    }
  }
  
  // Log the parsed options
  console.log("Parsed options:", parsedOptions);
  
  // Safety check for undefined options
  if (!parsedOptions) {
    console.error("prepareAuthenticationOptions received undefined or null options");
    throw new Error("Authentication options were not received properly from the server");
  }
  
  // Ensure we have required fields
  if (!parsedOptions.challenge) {
    console.error("Authentication options missing challenge");
    throw new Error("Authentication challenge is missing");
  }
  
  if (!parsedOptions.allowCredentials || !Array.isArray(parsedOptions.allowCredentials) || parsedOptions.allowCredentials.length === 0) {
    console.error("Authentication options missing allowCredentials");
    throw new Error("No credentials found for this user");
  }
  
  // Create a deep copy to avoid modifying the original
  const preparedOptions = JSON.parse(JSON.stringify(parsedOptions));
  
  // Convert challenge to ArrayBuffer
  preparedOptions.challenge = base64urlToArrayBuffer(parsedOptions.challenge);
  
  // Convert allowed credentials if present
  if (preparedOptions.allowCredentials) {
    preparedOptions.allowCredentials = preparedOptions.allowCredentials.map(cred => {
      if (!cred.id) {
        console.error("Credential missing ID:", cred);
        throw new Error("Invalid credential format received from server");
      }
      
      return {
        ...cred,
        id: base64urlToArrayBuffer(cred.id)
      };
    });
  }
  
  console.log("Prepared authentication options ready:", preparedOptions);
  return preparedOptions;
}

/**
 * Prepare WebAuthn credential for sending to server
 * @param {PublicKeyCredential} credential - Credential from browser
 * @returns {Object} - Prepared credential with base64url-encoded data
 */
function prepareCredentialForServer(credential) {
  // Basic credential data
  const serverCredential = {
    id: credential.id,
    rawId: arrayBufferToBase64url(credential.rawId),
    type: credential.type,
    response: {}
  };
  
  // Handle attestation response (registration)
  if (credential.response.attestationObject) {
    serverCredential.response.clientDataJSON = arrayBufferToBase64url(credential.response.clientDataJSON);
    serverCredential.response.attestationObject = arrayBufferToBase64url(credential.response.attestationObject);
  }
  
  // Handle assertion response (authentication)
  if (credential.response.signature) {
    serverCredential.response.clientDataJSON = arrayBufferToBase64url(credential.response.clientDataJSON);
    serverCredential.response.authenticatorData = arrayBufferToBase64url(credential.response.authenticatorData);
    serverCredential.response.signature = arrayBufferToBase64url(credential.response.signature);
    
    if (credential.response.userHandle) {
      serverCredential.response.userHandle = arrayBufferToBase64url(credential.response.userHandle);
    }
  }
  
  // Add transport information if available
  if (credential.response.getTransports) {
    serverCredential.transports = credential.response.getTransports();
  }
  
  return serverCredential;
}

/**
 * Register a new passkey
 * @param {string} url - Registration endpoint URL
 * @param {Object} options - Options to pass to the server
 * @param {function} callback - Callback function called after registration
 */
async function registerPasskey(url, options, callback) {
  try {
    // Start registration
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(options)
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to start registration');
    }
    
    const registrationOptions = await response.json();
    
    // Prepare options for browser
    const preparedOptions = prepareRegistrationOptions(registrationOptions);
    
    // Create credential
    const credential = await navigator.credentials.create({
      publicKey: preparedOptions
    });
    
    // Prepare credential for server
    const serverCredential = prepareCredentialForServer(credential);
    
    // Execute callback with prepared credential
    if (callback) {
      callback(serverCredential);
    }
    
    return serverCredential;
  } catch (error) {
    console.error('Registration error:', error);
    throw error;
  }
}

/**
 * Authenticate with a passkey
 * @param {string} url - Authentication endpoint URL
 * @param {Object} options - Options to pass to the server
 * @param {function} callback - Callback function called after authentication
 */
async function authenticateWithPasskey(url, options, callback) {
  try {
    // Start authentication
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(options)
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to start authentication');
    }
    
    const authOptions = await response.json();
    
    // Prepare options for browser
    const preparedOptions = prepareAuthenticationOptions(authOptions);
    
    // Get credential
    const credential = await navigator.credentials.get({
      publicKey: preparedOptions
    });
    
    // Prepare credential for server
    const serverCredential = prepareCredentialForServer(credential);
    
    // Execute callback with prepared credential
    if (callback) {
      callback(serverCredential);
    }
    
    return serverCredential;
  } catch (error) {
    console.error('Authentication error:', error);
    throw error;
  }
}

// Export for module environments, attach to window for direct browser use
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    base64urlToArrayBuffer,
    arrayBufferToBase64url,
    prepareRegistrationOptions,
    prepareAuthenticationOptions,
    prepareCredentialForServer,
    registerPasskey,
    authenticateWithPasskey
  };
} else {
  window.WebAuthnHelper = {
    base64urlToArrayBuffer,
    arrayBufferToBase64url,
    prepareRegistrationOptions,
    prepareAuthenticationOptions,
    prepareCredentialForServer,
    registerPasskey,
    authenticateWithPasskey
  };
}