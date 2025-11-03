# Locus Receipt Splitter

An agentic payment platform that automatically splits receipts and requests USDC payments using AI-powered receipt parsing.

## Features

- 📸 Upload receipt images for automatic parsing
- 🤖 AI-powered item extraction using GPT-4o-mini via LangChain
- 👥 Manage people and assign items
- 💰 Automatic calculation of splits including tax and tip
- 💳 Payment requests via Locus (coming soon)

## Architecture

- **Frontend**: React + TypeScript + Tailwind CSS + Vite
- **Backend**: FastAPI (Python) + LangChain + OpenAI
- **AI**: GPT-4o-mini for vision-based receipt parsing

## Getting Started

### Prerequisites

- Node.js (v18+)
- Python 3.8+
- OpenAI API key

### Setup

#### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up your OpenAI API key
cp .env.example .env
# Then edit .env and add your actual API key:
# OPENAI_API_KEY=sk-your-actual-api-key-here
```

#### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
```

### Running the Application

You need to run both the backend and frontend servers.

#### Terminal 1 - Backend

```bash
cd backend
source venv/bin/activate  # Activate virtual environment if not already active
python main.py
```

The backend API will start at `http://localhost:8000`

#### Terminal 2 - Frontend

```bash
cd frontend
npm run dev
```

The frontend will start at `http://localhost:5173`

### Usage

1. **Upload Receipt**: Click the "Upload" button and select a receipt image
2. **Add People**: Add the names of people who shared the receipt
3. **Set Payer**: Click "Set as Payer" next to the person who paid the original bill
4. **Assign Items**: Use the dropdowns to assign each item to a person
5. **Adjust Tax/Tip**: Modify the percentage values if needed
6. **Request Payment**: Click "Request Payment" to process (Locus integration coming soon)

## API Endpoints

### Backend (Port 8000)

- `GET /` - Health check
- `POST /upload-receipt` - Upload receipt image for parsing
  - Accepts: multipart/form-data with image file
  - Returns: JSON with extracted items

## Development

### Frontend
```bash
cd frontend
npm run dev  # Development server with hot reload
npm run build  # Build for production
```

### Backend
```bash
cd backend
python main.py  # Run development server
```

## Project Structure

```
locus-receipt-splitter/
├── frontend/           # React frontend
│   ├── src/
│   │   ├── App.tsx    # Main application component
│   │   └── ...
│   └── package.json
├── backend/            # FastAPI backend
│   ├── main.py        # Main API server
│   ├── requirements.txt
│   └── README.md
└── README.md
```

## How It Works

### Complete User Flow

1. **Upload Receipt**: User uploads a receipt image
   - Frontend sends image to `/upload-receipt`
   - Backend uses GPT-4o-mini to extract items (name, quantity, price)
   - Items populate in the UI

2. **Add People**: User adds people who shared the receipt
   - Names are entered manually
   - One person is marked as "Payer" (who paid originally)

3. **Assign Items**: User assigns each item to a person
   - Dropdowns show all people
   - Each item must be assigned

4. **Adjust Tax/Tip**: Modify percentages as needed (default 5% tax, 20% tip)

5. **Request Payment**: Click "Request Payment" button
   - Frontend sends all data to `/request-payment`
   - Backend connects to Locus MCP
   - **Payments always go to PERSON3** (hardcoded as the payer)
   - Backend sends USDC from each person to PERSON3 for their owed amount
   - Transaction results display on frontend

### Payment Processing

When "Request Payment" is clicked:
1. Backend maps person names to wallet addresses (PERSON1, PERSON2, PERSON3)
2. Connects to Locus MCP with agent credentials
3. For each person who owes money:
   - Calculates their share (items + proportional tax/tip)
   - Sends USDC payment via Locus to PERSON3
4. Returns transaction results (success/failed for each payment)
5. Frontend displays results with wallet addresses and status

**Note**: PERSON3 is always the recipient of all payments (hardcoded assumption that PERSON3 put down their card).

## Environment Variables

Your `.env` file should contain:

```bash
# OpenAI (for receipt parsing)
OPENAI_API_KEY=sk-proj-...

# Locus MCP (for payments)
AGENT_CLIENT_ID=your-locus-client-id
AGENT_CLIENT_SECRET=your-locus-client-secret

# Smart Wallets (for payment routing)
PERSON1_ADDRESS=0x...
PERSON1_PRIVATE_KEY=0x...
PERSON2_ADDRESS=0x...
PERSON2_PRIVATE_KEY=0x...
PERSON3_ADDRESS=0x...  # Always receives payments
PERSON3_PRIVATE_KEY=0x...
```

## API Endpoints

### Backend (Port 8000)

#### `GET /`
Health check

#### `POST /upload-receipt`
Upload receipt image for AI parsing
- **Request**: multipart/form-data with image file
- **Response**:
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

#### `POST /request-payment`
Process USDC payments via Locus
- **Request**:
  ```json
  {
    "items": [...],
    "people": [...],
    "paidBy": "PersonName",
    "subtotal": 10.0,
    "tax": 0.5,
    "tip": 2.0,
    "total": 12.5,
    "owedAmounts": {
      "Person1": 5.0,
      "Person2": 7.5
    }
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "transactions": [
      {
        "from": "Person1",
        "fromAddress": "0x...",
        "to": "Payer",
        "toAddress": "0x...",
        "amount": 5.0,
        "status": "success",
        "result": "..."
      }
    ],
    "total_processed": 2
  }
  ```

## Testing Locus Integration

Two test scripts are available in `/backend`:

1. **`test_locus_direct.py`** - Direct MCP tool calls (recommended)
   - No AI agent needed
   - Tests sending 0.01 USDC from PERSON1 to PERSON2
   - Run: `python test_locus_direct.py`

2. **`test_locus_transaction.py`** - AI agent approach
   - Requires Anthropic API key
   - Uses Claude to understand natural language
   - Run: `python test_locus_transaction.py`

See `backend/LOCUS_TEST.md` for detailed testing instructions.

## Future Enhancements

- [ ] Split items between multiple people
- [ ] Dynamic payer selection (instead of hardcoded PERSON3)
- [ ] Wallet authentication
- [ ] Payment history tracking
- [ ] Multi-currency support
- [ ] Support for more than 3 people
- [ ] Transaction confirmation on blockchain
