"""
Simple script to send 0.01 USDC from PERSON1 to PERSON3 using Locus MCP.
"""

import asyncio
import os
from dotenv import load_dotenv
from langchain_mcp_m2m import MCPClientCredentials

# Load environment variables
load_dotenv()

async def send_usdc():
    """Send 0.01 USDC from PERSON1 to PERSON3"""

    print("🚀 Sending USDC via Locus MCP")
    print("=" * 60)

    # Load credentials from .env
    locus_client_id = os.getenv("AGENT_CLIENT_ID")
    locus_client_secret = os.getenv("AGENT_CLIENT_SECRET")

    person1_address = os.getenv("PERSON1_ADDRESS")
    person3_address = os.getenv("PERSON3_ADDRESS")

    # Validate credentials
    if not locus_client_id or not locus_client_secret:
        raise ValueError("❌ AGENT_CLIENT_ID and AGENT_CLIENT_SECRET must be set in .env file")

    if not person1_address or not person3_address:
        raise ValueError("❌ PERSON1_ADDRESS and PERSON3_ADDRESS must be set in .env file")

    print(f"✅ Loaded credentials")
    print(f"   From: {person1_address}")
    print(f"   To: {person3_address}")
    print(f"   Amount: 0.01 USDC")
    print()

    # 1. Create MCP client with Client Credentials
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

    # 2. Initialize and load tools
    print("🔧 Initializing connection and loading tools...")
    await client.initialize()
    tools = await client.get_tools()

    print(f"✅ Loaded {len(tools)} tools from Locus MCP")
    print("\nAvailable tools:")
    for i, tool in enumerate(tools, 1):
        print(f"  {i}. {tool.name}")
        if hasattr(tool, 'description'):
            print(f"     {tool.description}")
    print()

    # 3. Find the send_to_address tool
    print("🔍 Looking for send_to_address tool...")
    payment_tool = None

    for tool in tools:
        if tool.name == "send_to_address":
            payment_tool = tool
            print(f"✅ Found: {tool.name}")
            break

    if not payment_tool:
        print("❌ Could not find send_to_address tool.")
        print("Available tools are listed above.")
        return

    print(f"   Description: {payment_tool.description if hasattr(payment_tool, 'description') else 'N/A'}")
    print(f"   Args schema: {payment_tool.args if hasattr(payment_tool, 'args') else 'N/A'}")
    print()

    # 4. Prepare transaction parameters
    print("💸 Preparing transaction...")
    transaction_params = {
        "address": person3_address,
        "amount": 0.01,
        "memo": "Test payment from send_usdc.py"
    }

    print("Parameters:")
    for key, value in transaction_params.items():
        print(f"  {key}: {value}")
    print()

    # 5. Execute the transaction
    print("⚡ Executing transaction...")
    print("-" * 60)

    try:
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
        print("Possible issues:")
        print("  - Incorrect parameter names (check args schema above)")
        print("  - Insufficient balance in sender wallet")
        print("  - Invalid addresses")
        print("  - Network issues")
        print()

    print("=" * 60)
    print("✨ Done!")

if __name__ == "__main__":
    asyncio.run(send_usdc())
