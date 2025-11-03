"""
Test script to send a small USDC transaction using Locus MCP - Direct Tool Calls.
Sends 0.01 USDC from PERSON1 to PERSON2 by directly calling MCP tools.
"""

import asyncio
import os
from dotenv import load_dotenv
from langchain_mcp_m2m import MCPClientCredentials

# Load environment variables
load_dotenv()

async def test_locus_direct_transaction():
    """Send a test transaction from PERSON1 to PERSON2 using direct MCP tool calls"""

    print("🚀 Starting Locus MCP Direct Transaction Test...")
    print("=" * 60)

    # Load credentials from .env
    locus_client_id = os.getenv("AGENT_CLIENT_ID")
    locus_client_secret = os.getenv("AGENT_CLIENT_SECRET")

    person1_address = os.getenv("PERSON1_ADDRESS")
    person2_address = os.getenv("PERSON2_ADDRESS")

    # Validate credentials
    if not locus_client_id or not locus_client_secret:
        raise ValueError("AGENT_CLIENT_ID and AGENT_CLIENT_SECRET must be set in .env file")

    if not person1_address or not person2_address:
        raise ValueError("PERSON1_ADDRESS and PERSON2_ADDRESS must be set in .env file")

    print(f"✅ Loaded credentials")
    print(f"   From: {person1_address}")
    print(f"   To: {person2_address}")
    print()

    # 1. Create MCP client with Locus credentials
    print("🔌 Connecting to Locus MCP server...")
    client = MCPClientCredentials({
        "locus": {
            "url": "https://mcp.paywithlocus.com/mcp",
            "transport": "streamable_http",
            "auth": {
                "client_id": locus_client_id,
                "client_secret": locus_client_secret
            }
        }
    })

    # 2. Initialize connection and load tools
    print("🔧 Initializing connection and loading tools...")
    await client.initialize()
    tools = await client.get_tools()

    print(f"✅ Loaded {len(tools)} tools from Locus MCP")
    print()
    print("Available tools:")
    for i, tool in enumerate(tools, 1):
        print(f"{i}. {tool.name}")
        print(f"   Description: {tool.description}")
        print(f"   Args: {tool.args}")
        print()

    # 3. Find the payment/transfer tool
    print("-" * 60)
    print("🔍 Looking for payment/transfer tool...")

    # Common tool names for sending payments
    payment_tool_keywords = ['send', 'transfer', 'pay', 'payment', 'transaction']
    payment_tool = None

    for tool in tools:
        tool_name_lower = tool.name.lower()
        if any(keyword in tool_name_lower for keyword in payment_tool_keywords):
            payment_tool = tool
            print(f"✅ Found payment tool: {tool.name}")
            break

    if not payment_tool:
        print("❌ Could not find a payment tool automatically.")
        print("Available tools are listed above. Please check the Locus documentation")
        print("or try selecting a tool manually.")
        return

    print(f"Tool: {payment_tool.name}")
    print(f"Description: {payment_tool.description}")
    print(f"Required arguments: {payment_tool.args}")
    print()

    # 4. Prepare transaction parameters
    print("💸 Preparing transaction...")

    # Based on common patterns, prepare the arguments
    # You may need to adjust these based on the actual tool schema
    transaction_params = {
        "from": person1_address,
        "to": person2_address,
        "amount": "0.01",  # 0.01 USDC
        "token": "USDC",  # Assuming USDC token
    }

    print(f"Transaction parameters:")
    for key, value in transaction_params.items():
        print(f"  {key}: {value}")
    print()

    # 5. Execute the transaction
    print("⚡ Executing transaction...")
    print("-" * 60)

    try:
        # Invoke the tool directly
        result = await payment_tool.ainvoke(transaction_params)

        print("-" * 60)
        print()
        print("✅ Transaction Complete!")
        print()
        print("📋 Result:")
        print(result)
        print()

    except Exception as e:
        print("-" * 60)
        print()
        print("❌ Transaction failed!")
        print(f"Error: {str(e)}")
        print()
        print("This might be due to:")
        print("  - Incorrect parameter names (check tool.args above)")
        print("  - Insufficient balance in sender wallet")
        print("  - Invalid addresses")
        print("  - Network issues")
        print()
        print("Try adjusting the transaction_params based on the tool's required arguments.")

    print("=" * 60)
    print("✨ Test complete!")

if __name__ == "__main__":
    asyncio.run(test_locus_direct_transaction())
