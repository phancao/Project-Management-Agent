# OpenProject v13.4.1 API Research

## API Documentation Summary

Based on research and testing:

### Authentication Methods

OpenProject v13.4.1 supports multiple authentication methods:

1. **API Key through Basic Auth** (Primary method for scripts)
   - Username: `apikey`
   - Password: Your API token
   - Format: `Authorization: Basic base64(apikey:TOKEN)`

2. **Session-based Authentication**
   - Uses cookies after web login

3. **OAuth2.0 Authentication**
   - Token-based OAuth2.0 flow

4. **OIDC Provider Generated JWT**
   - Bearer token from OpenID Connect provider

### API Structure

- **API v3**: General-purpose HATEOAS API
- **Format**: HAL+JSON (Hypertext Application Language)
- **Base URL**: `/api/v3`
- **Response format**: Includes `_type`, `_links`, `_embedded` properties

### Generating API Tokens

1. Log in to OpenProject
2. Navigate to: **My Account** → **Access Token**
3. Click **Generate** in the API section
4. Copy token immediately (shown only once)

### Token Authentication Issue (RESOLVED)

### Root Cause

**Problem**: API tokens from the restored database were stored as **plain text**, but OpenProject v13.4.1 expects tokens to be **hashed** using SHA256 with `Rails.application.secret_key_base` as salt.

**How it works**:
- `Token::API` inherits from `HashedToken`
- When creating a token, OpenProject generates a plain value and stores `SHA256(plain_value + secret_key_base)` in the database
- During authentication, it hashes the provided token and compares it to the stored hash
- Old tokens from restored database had plain values stored, causing authentication to fail

### Solution

**Create new tokens** via Rails console after database restore:

```ruby
user = User.find_by(mail: "your-email@example.com")
Token::API.where(user: user).destroy_all  # Remove old plain-text tokens
token = Token::API.create!(user: user)
puts token.plain_value  # Use this value for API authentication
```

**Important**: The `plain_value` is only available immediately after creation. Store it securely.

### Authentication Flow

1. User provides token via Basic Auth: `apikey:TOKEN`
2. OpenProject calls `User.find_by_api_key(token)`
3. Which calls `Token::API.find_by_plaintext_value(token)`
4. Which hashes the token and looks up: `Token::API.find_by(value: SHA256(token + secret_key_base))`
5. If found and user is active, authentication succeeds

### Current Status

✅ **RESOLVED**: New tokens work correctly. Old tokens from restored database need to be regenerated.

## References

- [OpenProject API Documentation](https://www.openproject.org/docs/api/)
- [OpenProject API Introduction](https://www.openproject.org/docs/api/introduction/)

