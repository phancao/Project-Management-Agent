# Development Scripts

This directory contains scripts to help with local development.

## Scripts

### `start_docker_services.sh`
Starts Docker services (PostgreSQL, Redis, OpenProject, etc.) with API key loaded from `conf.yaml`.

**Usage:**
```bash
# Start all services
./scripts/dev/start_docker_services.sh

# Start specific services
./scripts/dev/start_docker_services.sh api postgres redis
```

**Features:**
- Automatically extracts `OPENAI_API_KEY` from `conf.yaml`
- Sets the environment variable before starting docker-compose
- Falls back to environment variable if conf.yaml is not found

### `start_all_servers.sh`
Starts all servers (Docker services, backend, and frontend).

**Usage:**
```bash
./scripts/dev/start_all_servers.sh
```

**What it does:**
1. Loads API key from `conf.yaml`
2. Starts Docker services (OpenProject, PostgreSQL, etc.)
3. Starts backend server (if not already running)
4. Starts frontend server (if not already running)

### `start_backend_with_logs.sh`
Starts the backend server with logs visible in the terminal.

**Usage:**
```bash
./scripts/dev/start_backend_with_logs.sh
```

### `check_servers.sh`
Checks the status of all running servers.

**Usage:**
```bash
./scripts/dev/check_servers.sh
```

## Configuration

The scripts automatically load the OpenAI API key from `conf.yaml`:

```yaml
BASIC_MODEL:
  api_key: your-api-key-here
```

If `conf.yaml` is not found or doesn't contain an API key, the scripts will use the `OPENAI_API_KEY` environment variable if set.

## Notes

- The scripts use Python3 to parse YAML files (most reliable method)
- If Python3 is not available, the scripts fall back to grep/awk (less reliable)
- Environment variables take precedence over `conf.yaml` in docker-compose
- Make sure `conf.yaml` is in the project root directory
