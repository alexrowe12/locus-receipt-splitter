"""
Test script to send a small USDC transaction using Locus MCP.
Sends 0.01 USDC from PERSON1 to PERSON2.
"""

import asyncio
import os
from dotenv import load_dotenv
from langchain_mcp_m2m import MCPClientCredentials
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

# Load environment variables
load_dotenv()

async def test_locus_transaction():
    """Send a test transaction from PERSON1 to PERSON2"""

    print("🚀 Starting Locus MCP Test Transaction...")
    print("=" * 60)

    # Load credentials from .env
    locus_client_id = os.getenv("AGENT_CLIENT_ID")
    locus_client_secret = os.getenv("AGENT_CLIENT_SECRET")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

    person1_address = os.getenv("PERSON1_ADDRESS")
    person2_address = os.getenv("PERSON2_ADDRESS")

    # Validate credentials
    if not locus_client_id or not locus_client_secret:
        raise ValueError("AGENT_CLIENT_ID and AGENT_CLIENT_SECRET must be set in .env file")

    if not anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY must be set in .env file. Get one from https://console.anthropic.com/")

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
    print("   Available tools:")
    for tool in tools:
        print(f"   - {tool.name}")
    print()

    # 3. Create Claude agent with tools
    print("🤖 Creating AI agent with Claude...")
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        api_key=anthropic_api_key
    )
    agent = create_react_agent(llm, tools)

    # 4. Send transaction using natural language
    print("💸 Sending 0.01 USDC transaction...")
    print()

    query = f"""
    Send 0.01 USDC from {person1_address} to {person2_address}.
    Please confirm the transaction was successful.
    """

    print(f"Agent Query: {query.strip()}")
    print()
    print("Agent is processing...")
    print("-" * 60)

    result = await agent.ainvoke({
        "messages": [{"role": "user", "content": query}]
    })

    # Print result
    print("-" * 60)
    print()
    print("📋 Agent Response:")
    print()

    # Extract the final message from the agent
    messages = result.get("messages", [])
    if messages:
        final_message = messages[-1]
        print(final_message.content)
    else:
        print(result)

    print()
    print("=" * 60)
    print("✨ Test complete!")

if __name__ == "__main__":
    asyncio.run(test_locus_transaction())
