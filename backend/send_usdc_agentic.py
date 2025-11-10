"""
Agentic script to send USDC using Claude AI and Locus MCP.
Prompts Claude to send 4.11 USDC to PERSON1 and 4.14 USDC to PERSON2.
"""

import asyncio
import os
from dotenv import load_dotenv
from langchain_mcp_m2m import MCPClientCredentials
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

# Load environment variables
load_dotenv()

async def send_usdc_agentic():
    """Use Claude AI to send multiple USDC payments from Person 3"""

    print("🤖 Agentic USDC Transfer via Claude AI + Locus MCP")
    print("=" * 60)

    # Load credentials from .env (using Person 3 to send)
    locus_client_id = os.getenv("PERSON3_CLIENT_ID")
    locus_client_secret = os.getenv("PERSON3_CLIENT_SECRET")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

    person1_address = os.getenv("PERSON1_ADDRESS")
    person2_address = os.getenv("PERSON2_ADDRESS")
    person3_address = os.getenv("PERSON3_ADDRESS")

    # Validate credentials
    if not locus_client_id or not locus_client_secret:
        raise ValueError("❌ PERSON3_CLIENT_ID and PERSON3_CLIENT_SECRET must be set in .env file")

    if not anthropic_api_key:
        raise ValueError("❌ ANTHROPIC_API_KEY must be set in .env file")

    if not person1_address or not person2_address or not person3_address:
        raise ValueError("❌ PERSON1_ADDRESS, PERSON2_ADDRESS, and PERSON3_ADDRESS must be set in .env file")

    print(f"✅ Loaded credentials")
    print(f"   Sending from: Person 3 ({person3_address})")
    print(f"   Sending to:")
    print(f"      Person 1: {person1_address}")
    print(f"      Person 2: {person2_address}")
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
    print("✅ Agent ready!")
    print()

    # 4. Send transactions using natural language
    print("💸 Sending USDC payments via AI agent...")
    print()

    query = f"""
    Please send two USDC payments:
    1. Send 4.11 USDC to {person1_address} with memo "Payment to Person 1"
    2. Send 4.14 USDC to {person2_address} with memo "Payment to Person 2"

    Please confirm both transactions were successful.
    """

    print(f"📝 Agent Query:")
    print(f"   {query.strip()}")
    print()
    print("🔄 Agent is processing...")
    print("-" * 60)

    result = await agent.ainvoke({
        "messages": [{"role": "user", "content": query}]
    })

    # Print result
    print("-" * 60)
    print()
    print("🤖 Agent Response:")
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
    print("✨ Done!")

if __name__ == "__main__":
    asyncio.run(send_usdc_agentic())
