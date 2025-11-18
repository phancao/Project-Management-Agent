# Testing Guide - Project Management Agent

Hướng dẫn chi tiết về cách test từng phần của hệ thống Project Management Agent.

## 📁 Test Organization

The project has two types of test files:

1. **Official Test Suite** (`tests/` directory): Automated unit and integration tests run via pytest
2. **Standalone Test Scripts** (`scripts/tests/` directory): Manual testing, debugging, and validation scripts

### Creating New Test Scripts

**For AI Assistants**: When creating new test scripts:
- **Standalone/debugging scripts**: Create in `scripts/tests/` directory
- **Unit/integration tests**: Create in `tests/` directory (follow pytest conventions)
- See `scripts/tests/README.md` for detailed guidelines

## 🚀 Quick Start

### Chạy test nhanh
```bash
# Test nhanh tất cả components
python quick_test.py

# Hoặc sử dụng Makefile
make test
```

### Chạy test chi tiết
```bash
# Test tất cả
python run_tests.py all

# Test từng phần
python run_tests.py deerflow
python run_tests.py conversation
python run_tests.py database
python run_tests.py api
```

### Chạy standalone test scripts
```bash
# Run standalone test scripts (manual testing/debugging)
python scripts/tests/test_openproject_all_pagination.py
```

## 📋 Test Suites

### 1. DeerFlow Integration Tests (`tests/test_deerflow.py`)

**Mục đích**: Test tích hợp DeerFlow với OpenAI API

**Các test bao gồm**:
- ✅ Import các module DeerFlow
- ✅ Kết nối LLM với OpenAI API
- ✅ Xây dựng graph workflow
- ✅ Chạy workflow đơn giản
- ✅ Chạy workflow research
- ✅ Kiểm tra configuration

**Chạy test**:
```bash
python run_tests.py deerflow
# hoặc
python tests/test_deerflow.py
```

**Kết quả mong đợi**:
```
🦌 Running DeerFlow Integration Tests...
✅ Configuration loaded successfully
✅ LLM import successful
✅ Graph builder import successful
✅ Workflow import successful
✅ LLM connection works
✅ Graph built successfully
✅ Workflow completed successfully
🎉 All tests passed! DeerFlow integration is working correctly.
```

### 2. Conversation Flow Manager Tests (`tests/test_conversation_flow.py`)

**Mục đích**: Test hệ thống quản lý conversation flow

**Các test bao gồm**:
- ✅ Import conversation flow manager
- ✅ Phân loại intent từ message
- ✅ Tạo câu hỏi clarification
- ✅ Quản lý context conversation
- ✅ Validation dữ liệu
- ✅ Chuyển đổi trạng thái flow
- ✅ Luồng conversation hoàn chỉnh

**Chạy test**:
```bash
python run_tests.py conversation
# hoặc
python tests/test_conversation_flow.py
```

**Kết quả mong đợi**:
```
💬 Running Conversation Flow Manager Tests...
✅ Conversation Flow Manager imports successful
✅ Intent classification works
✅ Question generation works
✅ Data validation works
✅ Context management works
✅ Flow state transitions work
✅ Complete conversation flow works
🎉 All tests passed! Conversation Flow Manager is working correctly.
```

### 3. Database Model Tests (`tests/test_database.py`)

**Mục đích**: Test các model database và validation

**Các test bao gồm**:
- ✅ Import database models
- ✅ Tạo và validation models
- ✅ Test enum values
- ✅ Test relationships giữa models
- ✅ Test JSON serialization
- ✅ Test optional fields
- ✅ Test timestamps
- ✅ Test UUID generation

**Chạy test**:
```bash
python run_tests.py database
# hoặc
python tests/test_database.py
```

**Kết quả mong đợi**:
```
🗄️ Running Database Tests...
✅ Database models import successful
✅ Model creation works
✅ Model validation works
✅ Enum values work
✅ Relationships work
✅ JSON serialization works
✅ Optional fields work
✅ Timestamps work
✅ UUID generation works
🎉 All tests passed! Database models are working correctly.
```

### 4. FastAPI Endpoint Tests (`tests/test_api.py`)

**Mục đích**: Test các API endpoints và WebSocket

**Các test bao gồm**:
- ✅ Import FastAPI app
- ✅ Health check endpoint
- ✅ Chat endpoints
- ✅ Project management endpoints
- ✅ Task management endpoints
- ✅ Research endpoints
- ✅ Knowledge base endpoints
- ✅ WebSocket connection
- ✅ Data validation
- ✅ Error handling

**Chạy test**:
```bash
python run_tests.py api
# hoặc
python tests/test_api.py
```

**Kết quợi mong đợi**:
```
🔌 Running FastAPI Tests...
✅ FastAPI app import successful
✅ Health check works
✅ Chat endpoints work
✅ Project endpoints work
✅ Task endpoints work
✅ Research endpoints work
✅ Knowledge endpoints work
✅ WebSocket connection works
✅ Data validation works
✅ Error handling works
🎉 All tests passed! FastAPI is working correctly.
```

## 🛠️ Development Testing

### Chạy development environment
```bash
# Start all services
make dev

# Hoặc manual
docker-compose up -d postgres redis
uv run uvicorn api.main:app --reload --port 8000
cd frontend && npm run dev
```

### Test với Docker
```bash
# Build và test với Docker
docker-compose up --build

# Test specific service
docker-compose up api
docker-compose up frontend
```

## 🔧 Troubleshooting

### Lỗi thường gặp

#### 1. DeerFlow tests fail
```
❌ LLM connection failed: AuthenticationError
```
**Giải pháp**: Kiểm tra API key trong `conf.yaml`

#### 2. Conversation tests fail
```
❌ Conversation Flow Manager imports failed: ModuleNotFoundError
```
**Giải pháp**: Chạy `uv sync` để cài dependencies

#### 3. API tests fail
```
❌ FastAPI app import failed: ImportError
```
**Giải pháp**: Kiểm tra imports trong `api/main.py`

#### 4. Database tests fail
```
❌ Database models import failed: ImportError
```
**Giải pháp**: Kiểm tra file `database/models.py`

### Debug mode
```bash
# Chạy test với debug output
python -u tests/test_deerflow.py

# Chạy với verbose output
python run_tests.py deerflow --verbose
```

## 📊 Test Coverage

### Kiểm tra coverage
```bash
# Install coverage tools
uv add pytest-cov

# Run tests with coverage
uv run pytest --cov=src --cov=api --cov=database tests/
```

### Coverage report
```bash
# Generate HTML coverage report
uv run pytest --cov=src --cov-report=html tests/
open htmlcov/index.html
```

## 🚀 Continuous Integration

### GitHub Actions (nếu có)
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: |
          pip install uv
          uv sync
      - name: Run tests
        run: python run_tests.py all
```

## 📝 Best Practices

### 1. Test Structure
- Mỗi test file test một component cụ thể
- Test cases rõ ràng và dễ hiểu
- Error messages chi tiết

### 2. Test Data
- Sử dụng mock data cho tests
- Clean up sau mỗi test
- Test với edge cases

### 3. Performance
- Test timeout để tránh hang
- Test với realistic data sizes
- Monitor test execution time

### 4. Maintenance
- Update tests khi thay đổi code
- Review test failures ngay lập tức
- Document test requirements

## 🎯 Next Steps

Sau khi tất cả tests pass:

1. **Start development server**:
   ```bash
   make dev
   ```

2. **Access the application**:
   - Frontend: http://localhost:3000
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

3. **Test manual integration**:
   - Tạo project mới
   - Test conversation flow
   - Test real-time chat

4. **Deploy to production**:
   ```bash
   make deploy
   ```

---

**Happy Testing! 🧪✨**
