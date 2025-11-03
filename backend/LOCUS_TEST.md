# Locus MCP Test Transactions

Two test scripts are available:

1. **`test_locus_direct.py`** - Direct tool calls (RECOMMENDED TO START)
   - No AI agent needed
   - No Anthropic API key required
   - Manually calls Locus MCP tools

2. **`test_locus_transaction.py`** - AI agent approach
   - Uses Claude AI to understand natural language
   - Requires Anthropic API key
   - Agent picks the right tool automatically

---

## Option 1: Direct Tool Calls (RECOMMENDED)

### Prerequisites

1. **Locus Credentials**: Already in your `.env`
   - `AGENT_CLIENT_ID`
   - `AGENT_CLIENT_SECRET`

2. **Wallet Addresses**: Already in your `.env`
   - `PERSON1_ADDRESS` and `PERSON2_ADDRESS`

### Setup

Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the Test

```bash
python test_locus_direct.py
```

### What It Does

The script:
1. Connects to Locus MCP using your agent credentials
2. Lists all available Locus tools
3. Finds the payment/transfer tool
4. Directly calls it to send 0.01 USDC from PERSON1 to PERSON2
5. Prints the result

### Expected Output

```
🚀 Starting Locus MCP Direct Transaction Test...
============================================================
✅ Loaded credentials
   From: 0x0f51b40F7285318B8710317b90
   To: 0x3304D21A0d436bDB18fcF11D73f3

🔌 Connecting to Locus MCP server...
🔧 Initializing connection and loading tools...
✅ Loaded X tools from Locus MCP

Available tools:
1. [tool name]
   Description: [description]
   Args: {...}

------------------------------------------------------------
🔍 Looking for payment/transfer tool...
✅ Found payment tool: [tool name]

💸 Preparing transaction...
Transaction parameters:
  from: 0x...
  to: 0x...
  amount: 0.01
  token: USDC

⚡ Executing transaction...
------------------------------------------------------------
✅ Transaction Complete!

📋 Result:
[Transaction details and confirmation]
============================================================
✨ Test complete!
```

---

## Option 2: AI Agent Approach

### Additional Prerequisites

1. **Anthropic API Key**: You need a Claude API key
   - Get one from: https://console.anthropic.com/
   - Add to your `.env` file: `ANTHROPIC_API_KEY=sk-ant-...`

### Setup

1. Install additional dependencies:
```bash
# Uncomment the agent dependencies in requirements.txt first
pip install langchain-anthropic langgraph
```

2. Add your Anthropic API key to `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Running the Test

```bash
python test_locus_transaction.py
```

### What It Does

The script:
1. Connects to Locus MCP
2. Loads available Locus tools
3. Creates a Claude AI agent with those tools
4. Asks the agent in natural language to send 0.01 USDC
5. The agent picks the right tool and executes it
6. Prints the result

---

## Troubleshooting

**Error: "AGENT_CLIENT_ID and AGENT_CLIENT_SECRET must be set"**
- Check your `.env` file has these credentials

**Error: Connection failed**
- Verify your Locus credentials are correct
- Check network connectivity

**Error: Tool invocation failed**
- The tool parameters might need adjustment
- Check the tool's `args` in the output
- Refer to Locus documentation for exact parameter names

**Error: Insufficient balance**
- Make sure PERSON1 wallet has at least 0.01 USDC

**Tool parameters don't match**
- The script auto-detects payment tools
- You may need to adjust `transaction_params` based on the actual tool schema
- Check the printed tool args and modify accordingly
