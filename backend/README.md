# Locus Receipt Splitter - Backend

FastAPI backend for processing receipt images using LangChain and ChatGPT.

## Setup

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file and add your OpenAI API key:
```bash
# Copy the example file
cp .env.example .env

# Then edit .env and add your actual API key
# .env should contain:
# OPENAI_API_KEY=sk-your-actual-api-key-here
```

4. Run the server:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### POST /upload-receipt
Accepts a receipt image and returns extracted items.

**Request:**
- File upload (multipart/form-data)
- Field name: `file`
- Accepts: image files (jpg, png, etc.)

**Response:**
```json
{
  "success": true,
  "items": [
    {
      "id": "1",
      "name": "Americano",
      "quantity": 1,
      "price": 0.01,
      "assignedTo": ""
    }
  ],
  "raw_response": "Americano,1,0.01\n..."
}
```
