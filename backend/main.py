from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_mcp_m2m import MCPClientCredentials
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
from pydantic import BaseModel
import base64
import io
import csv
import os
import re
from typing import List, Dict, Optional

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables. Please create a .env file with your API key.")

# Locus MCP configuration
LOCUS_CLIENT_ID = os.getenv("AGENT_CLIENT_ID")
LOCUS_CLIENT_SECRET = os.getenv("AGENT_CLIENT_SECRET")

# Wallet configuration - PERSON3 is always the payer
PERSON3_ADDRESS = os.getenv("PERSON3_ADDRESS")

# Pydantic models for request/response
class Item(BaseModel):
    id: str
    name: str
    quantity: int
    price: float
    assignedTo: str

class Person(BaseModel):
    id: str
    name: str

class PaymentRequest(BaseModel):
    items: List[Item]
    people: List[Person]
    paidBy: str
    subtotal: float
    tax: float
    tip: float
    total: float
    owedAmounts: Dict[str, float]

class NegotiationRequest(BaseModel):
    items: List[Item]
    person1_input: str
    person2_input: str
    person3_input: str

class ExecuteNegotiatedPayment(BaseModel):
    person1_amount: float
    person2_amount: float

@app.post("/upload-receipt")
async def upload_receipt(file: UploadFile = File(...)):
    """
    Accepts a receipt image and uses ChatGPT via LangChain to extract items.
    Returns a list of items with name, quantity, and price.
    """
    try:
        # Read the uploaded file
        contents = await file.read()

        # Encode image to base64
        base64_image = base64.b64encode(contents).decode('utf-8')

        # Determine image type
        image_type = file.content_type or "image/jpeg"

        # Initialize ChatGPT with vision capabilities
        chat = ChatOpenAI(
            model="gpt-4o-mini",  # Using gpt-4o-mini for vision
            api_key=OPENAI_API_KEY,
            temperature=0
        )

        # Create the message with the image
        message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": """Analyze this receipt image and extract all items purchased.
                    Return the data in CSV format with exactly 3 columns: name,quantity,price

                    Rules:
                    - Do NOT include headers in your response
                    - Each line should be: item_name,quantity,price
                    - quantity should be a number
                    - price should be the total price for that line item (quantity * unit price) as a decimal number
                    - Do NOT include currency symbols
                    - Do NOT include the subtotal, tax, or tip lines
                    - Only extract the actual purchased items

                    Example format:
                    Americano,1,0.01
                    Chocolate Chip Cookie,2,0.04
                    Coke,2,0.02
                    """
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{image_type};base64,{base64_image}"
                    }
                }
            ]
        )

        # Get response from ChatGPT
        response = chat.invoke([message])
        csv_text = response.content.strip()

        # Parse CSV response
        items = []
        csv_reader = csv.reader(io.StringIO(csv_text))

        for idx, row in enumerate(csv_reader, start=1):
            if len(row) >= 3:
                items.append({
                    "id": str(idx),
                    "name": row[0].strip(),
                    "quantity": int(row[1].strip()),
                    "price": float(row[2].strip()),
                    "assignedTo": ""  # Empty - user will assign
                })

        return {
            "success": True,
            "items": items,
            "raw_response": csv_text  # For debugging
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing receipt: {str(e)}"
        )

@app.post("/request-payment")
async def request_payment(payment_data: PaymentRequest):
    """
    Processes payment requests using Locus MCP.
    Sends USDC from each person to PERSON3 (the payer) for their owed amount.
    """
    try:
        # Validate Locus credentials
        if not LOCUS_CLIENT_ID or not LOCUS_CLIENT_SECRET:
            raise HTTPException(
                status_code=500,
                detail="Locus credentials not configured. Please set AGENT_CLIENT_ID and AGENT_CLIENT_SECRET in .env"
            )

        if not PERSON3_ADDRESS:
            raise HTTPException(
                status_code=500,
                detail="PERSON3_ADDRESS not configured in .env"
            )

        print("🚀 Processing payment request...")
        print(f"Total amount: ${payment_data.total:.2f}")
        print(f"Payments to be made to PERSON3: {PERSON3_ADDRESS}")

        # Connect to Locus MCP
        print("🔌 Connecting to Locus MCP...")
        client = MCPClientCredentials({
            "locus": {
                "url": "https://mcp.paywithlocus.com/mcp",
                "transport": "streamable_http",
                "auth": {
                    "client_id": LOCUS_CLIENT_ID,
                    "client_secret": LOCUS_CLIENT_SECRET
                }
            }
        })

        # Initialize and load tools
        await client.initialize()
        tools = await client.get_tools()

        print(f"✅ Loaded {len(tools)} tools from Locus MCP")

        # Find payment tool
        payment_tool_keywords = ['send', 'transfer', 'pay', 'payment', 'transaction', 'request']
        payment_tool = None

        for tool in tools:
            tool_name_lower = tool.name.lower()
            if any(keyword in tool_name_lower for keyword in payment_tool_keywords):
                payment_tool = tool
                print(f"✅ Found payment tool: {tool.name}")
                break

        if not payment_tool:
            raise HTTPException(
                status_code=500,
                detail="Could not find payment tool in Locus MCP"
            )

        # Process payments for each person who owes money
        transactions = []

        # Get the mapping of person names to wallet addresses
        # We need to map frontend person names to wallet addresses
        person_wallets = {}
        for i, person in enumerate(payment_data.people, 1):
            wallet_address = os.getenv(f"PERSON{i}_ADDRESS")
            if wallet_address:
                person_wallets[person.name] = wallet_address

        print(f"\n💸 Processing {len(payment_data.owedAmounts)} payment(s)...")

        for person_name, owed_amount in payment_data.owedAmounts.items():
            # Skip the payer (they don't pay themselves)
            if person_name == payment_data.paidBy:
                continue

            # Skip if amount is 0 or negative
            if owed_amount <= 0:
                continue

            # Get wallet address for this person
            from_address = person_wallets.get(person_name)

            if not from_address:
                print(f"⚠️  Warning: No wallet address found for {person_name}, skipping...")
                transactions.append({
                    "from": person_name,
                    "to": payment_data.paidBy,
                    "amount": owed_amount,
                    "status": "failed",
                    "error": "No wallet address configured"
                })
                continue

            print(f"\n   {person_name} → {payment_data.paidBy}: ${owed_amount:.2f}")
            print(f"   From: {from_address}")
            print(f"   To: {PERSON3_ADDRESS}")

            try:
                # Prepare transaction parameters
                # Adjust these based on the actual tool schema
                transaction_params = {
                    "from": from_address,
                    "to": PERSON3_ADDRESS,
                    "amount": str(owed_amount),
                    "token": "USDC",
                }

                # Execute payment
                result = await payment_tool.ainvoke(transaction_params)

                print(f"   ✅ Transaction successful")

                transactions.append({
                    "from": person_name,
                    "fromAddress": from_address,
                    "to": payment_data.paidBy,
                    "toAddress": PERSON3_ADDRESS,
                    "amount": owed_amount,
                    "status": "success",
                    "result": str(result)
                })

            except Exception as e:
                error_msg = str(e)
                print(f"   ❌ Transaction failed: {error_msg}")

                transactions.append({
                    "from": person_name,
                    "fromAddress": from_address,
                    "to": payment_data.paidBy,
                    "toAddress": PERSON3_ADDRESS,
                    "amount": owed_amount,
                    "status": "failed",
                    "error": error_msg
                })

        print(f"\n✨ Payment processing complete!")
        print(f"   Successful: {sum(1 for t in transactions if t['status'] == 'success')}")
        print(f"   Failed: {sum(1 for t in transactions if t['status'] == 'failed')}")

        return {
            "success": True,
            "transactions": transactions,
            "total_processed": len(transactions)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error processing payments: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing payments: {str(e)}"
        )

@app.post("/negotiate-payment")
async def negotiate_payment(negotiation_data: NegotiationRequest):
    """
    Runs a 3-agent negotiation where each person (represented by a Claude agent)
    argues about who should pay for what items. Runs 2 full cycles, then asks
    each agent to commit to a final amount they'll pay to Person 3.
    """
    try:
        # Load agent credentials for all 3 people
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

        agent_configs = []
        for i in range(1, 4):
            client_id = os.getenv(f"PERSON{i}_CLIENT_ID")
            client_secret = os.getenv(f"PERSON{i}_CLIENT_SECRET")
            person_address = os.getenv(f"PERSON{i}_ADDRESS")

            if not client_id or not client_secret:
                raise HTTPException(
                    status_code=500,
                    detail=f"PERSON{i}_CLIENT_ID and PERSON{i}_CLIENT_SECRET must be set in .env"
                )

            agent_configs.append({
                "client_id": client_id,
                "client_secret": client_secret,
                "address": person_address
            })

        if not anthropic_api_key:
            raise HTTPException(
                status_code=500,
                detail="ANTHROPIC_API_KEY must be set in .env"
            )

        print("🤖 Starting 3-agent negotiation...")

        # Calculate receipt totals (no tax/tip for now)
        total = sum(item.price for item in negotiation_data.items)

        # Prepare items description
        items_text = "\n".join([
            f"- {item.name} (Quantity: {item.quantity}, Price: ${item.price:.2f})"
            for item in negotiation_data.items
        ])

        # Create 3 separate agents, each with their own Locus MCP connection
        agents = []
        for i in range(1, 4):
            print(f"\n🔌 Creating agent for Person {i}...")

            # Create MCP client
            client = MCPClientCredentials({
                "locus": {
                    "url": "https://mcp.paywithlocus.com/mcp",
                    "transport": "streamable_http",
                    "auth": {
                        "client_id": agent_configs[i-1]["client_id"],
                        "client_secret": agent_configs[i-1]["client_secret"]
                    }
                }
            })

            # Initialize and load tools
            await client.initialize()
            tools = await client.get_tools()

            # Create Claude agent with tools
            llm = ChatAnthropic(
                model="claude-sonnet-4-20250514",
                api_key=anthropic_api_key
            )
            agent = create_react_agent(llm, tools)

            agents.append({
                "agent": agent,
                "person_num": i,
                "tools": tools
            })

            print(f"✅ Agent {i} ready with {len(tools)} Locus tools")

        # Run negotiation rounds
        conversation_history = []
        user_inputs = [
            negotiation_data.person1_input,
            negotiation_data.person2_input,
            negotiation_data.person3_input
        ]

        print("\n💬 Starting negotiation rounds...")

        # 2 full cycles = 6 messages total (Person 1, 2, 3, then 1, 2, 3 again)
        for cycle in range(2):
            print(f"\n--- Cycle {cycle + 1} ---")

            for person_idx in range(3):
                person_num = person_idx + 1
                agent_info = agents[person_idx]

                # Build context for this agent
                context_parts = [
                    f"You are representing Person {person_num} in a receipt splitting negotiation.",
                    f"Person 3 paid the bill upfront, so everyone owes money to Person 3.",
                    f"\nReceipt items:",
                    items_text,
                    f"\nTotal bill: ${total:.2f}",
                    f"\nYour instructions: {user_inputs[person_idx]}",
                ]

                # Add conversation history
                if conversation_history:
                    context_parts.append("\n--- Previous negotiation messages ---")
                    for msg in conversation_history:
                        context_parts.append(f"Person {msg['person']}: {msg['message']}")

                context_parts.append("\nRespond with your argument about who should pay for what. Be specific about items and amounts.")

                full_context = "\n".join(context_parts)

                print(f"\n👤 Person {person_num} is responding...")

                # Invoke agent
                result = await agent_info["agent"].ainvoke({
                    "messages": [{"role": "user", "content": full_context}]
                })

                # Extract response
                messages = result.get("messages", [])
                if messages:
                    response_text = messages[-1].content
                else:
                    response_text = str(result)

                print(f"   Response: {response_text[:100]}...")

                # Add to conversation history
                conversation_history.append({
                    "person": person_num,
                    "message": response_text
                })

        print("\n💰 Asking each agent for their final payment commitment...")

        # 7th round: Ask each agent what they're paying
        final_amounts = {}

        for person_idx in range(3):
            person_num = person_idx + 1
            agent_info = agents[person_idx]

            # Build final summary context
            summary_parts = [
                f"You are Person {person_num}.",
                f"Person 3 paid the bill upfront (${total:.2f} total).",
                f"\nReceipt items:",
                items_text,
                f"\nTotal bill: ${total:.2f}",
                f"\n--- Full negotiation transcript ---"
            ]

            for msg in conversation_history:
                summary_parts.append(f"Person {msg['person']}: {msg['message']}")

            if person_num == 3:
                summary_parts.append(
                    f"\n--- Final Commitment ---"
                    f"\nYou are Person 3 - the person who PAID UPFRONT."
                    f"\nYou do NOT need to pay anyone. You will RECEIVE money from the others."
                    f"\n\nBased on the negotiation above, you (Person 3) should respond with: 0"
                    f"\n\nRespond with ONLY the number: 0"
                )
            else:
                summary_parts.append(
                    f"\n--- Final Commitment ---"
                    f"\nYou are Person {person_num}. You need to pay Person 3 (who paid upfront)."
                    f"\n\nBased on the negotiation above, what is the EXACT dollar amount you will pay to Person 3?"
                    f"\n\nIMPORTANT REMINDER:"
                    f"\n- The total bill was only ${total:.2f} (that's {int(total * 100)} cents)"
                    f"\n- Amounts discussed were things like $0.01, $0.02, $0.03 (1 cent, 2 cents, 3 cents)"
                    f"\n- Your payment should be in the CENTS range, not whole dollars"
                    f"\n- DO NOT say 1.00 or 2.00 or 3.00 - those are WAY too large"
                    f"\n\nLook at your last message in the negotiation. You likely said something like '$0.03' or '$0.02'."
                    f"\nRespond with ONLY that number in decimal form (e.g., '0.03' or '0.02')."
                    f"\nDo NOT include the $ symbol. Just the number like: 0.03"
                )

            full_summary = "\n".join(summary_parts)

            print(f"\n👤 Person {person_num} committing to final amount...")

            # Invoke agent for final amount
            result = await agent_info["agent"].ainvoke({
                "messages": [{"role": "user", "content": full_summary}]
            })

            # Extract response
            messages = result.get("messages", [])
            if messages:
                response_text = messages[-1].content
            else:
                response_text = str(result)

            # Try to extract a number from the response
            # Look for dollar amounts or just numbers
            amount_match = re.search(r'\$?\s*(\d+\.?\d*)', response_text)
            if amount_match:
                amount = float(amount_match.group(1))
            else:
                amount = 0.0

            # Sanity check: if amount is way larger than the total bill, it's likely wrong
            # (e.g., they said "1.00" when they meant "0.01")
            if amount > total:
                print(f"   ⚠️  WARNING: Person {person_num} said ${amount:.2f} but total bill is only ${total:.2f}")
                print(f"   This seems like a decimal place error. Attempting to correct...")

                # Check if they meant cents but said dollars
                # e.g., if they said "1.00" but likely meant "0.01"
                corrected_amount = amount / 100
                if corrected_amount <= total:
                    print(f"   Corrected to: ${corrected_amount:.2f}")
                    amount = corrected_amount
                else:
                    print(f"   Could not auto-correct. Setting to 0.")
                    amount = 0.0

            print(f"   Person {person_num} commits: ${amount:.2f}")

            final_amounts[f"person{person_num}"] = amount

            # Add to conversation history
            if person_num == 3:
                # Person 3 receives money, doesn't pay
                total_receiving = final_amounts.get("person1", 0) + final_amounts.get("person2", 0)
                conversation_history.append({
                    "person": person_num,
                    "message": f"I will receive ${total_receiving:.2f} from the others (${final_amounts.get('person1', 0):.2f} from Person 1 and ${final_amounts.get('person2', 0):.2f} from Person 2)."
                })
            else:
                conversation_history.append({
                    "person": person_num,
                    "message": f"I will pay ${amount:.2f} to Person 3."
                })

        print("\n✨ Negotiation complete!")

        return {
            "success": True,
            "transcript": conversation_history,
            "final_amounts": final_amounts,
            "total": total
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error during negotiation: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error during negotiation: {str(e)}"
        )

@app.post("/execute-negotiated-payment")
async def execute_negotiated_payment(payment_data: ExecuteNegotiatedPayment):
    """
    Executes the payments that were negotiated by the agents.
    Person 1 and Person 2 each send their agreed amounts to Person 3.
    """
    try:
        # Load credentials
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        person3_address = os.getenv("PERSON3_ADDRESS")

        if not person3_address:
            raise HTTPException(
                status_code=500,
                detail="PERSON3_ADDRESS not configured in .env"
            )

        print("💸 Executing negotiated payments...")
        print(f"   Person 1 → Person 3: ${payment_data.person1_amount:.2f}")
        print(f"   Person 2 → Person 3: ${payment_data.person2_amount:.2f}")

        transactions = []

        # Process payments for Person 1 and Person 2
        for person_num in [1, 2]:
            amount = payment_data.person1_amount if person_num == 1 else payment_data.person2_amount

            # Skip if amount is 0 or negative
            if amount <= 0:
                print(f"   ⏭️  Skipping Person {person_num} (amount: ${amount:.2f})")
                continue

            client_id = os.getenv(f"PERSON{person_num}_CLIENT_ID")
            client_secret = os.getenv(f"PERSON{person_num}_CLIENT_SECRET")
            person_address = os.getenv(f"PERSON{person_num}_ADDRESS")

            if not client_id or not client_secret:
                raise HTTPException(
                    status_code=500,
                    detail=f"PERSON{person_num}_CLIENT_ID and PERSON{person_num}_CLIENT_SECRET must be set in .env"
                )

            print(f"\n🔌 Creating agent for Person {person_num} payment...")

            # Create MCP client for this person
            client = MCPClientCredentials({
                "locus": {
                    "url": "https://mcp.paywithlocus.com/mcp",
                    "transport": "streamable_http",
                    "auth": {
                        "client_id": client_id,
                        "client_secret": client_secret
                    }
                }
            })

            # Initialize and load tools
            await client.initialize()
            tools = await client.get_tools()

            # Create Claude agent
            llm = ChatAnthropic(
                model="claude-sonnet-4-20250514",
                api_key=anthropic_api_key
            )
            agent = create_react_agent(llm, tools)

            print(f"✅ Agent {person_num} ready, sending payment...")

            # Prompt the agent to send the payment
            payment_prompt = f"""
            Send ${amount:.2f} USDC to {person3_address}.
            Use the memo "Payment from negotiated receipt split".
            Please confirm the transaction was successful.
            """

            try:
                result = await agent.ainvoke({
                    "messages": [{"role": "user", "content": payment_prompt}]
                })

                # Extract response
                messages = result.get("messages", [])
                if messages:
                    response_text = messages[-1].content
                else:
                    response_text = str(result)

                print(f"   ✅ Transaction successful for Person {person_num}")

                transactions.append({
                    "from": f"Person {person_num}",
                    "fromAddress": person_address,
                    "to": "Person 3",
                    "toAddress": person3_address,
                    "amount": amount,
                    "status": "success",
                    "result": response_text
                })

            except Exception as e:
                error_msg = str(e)
                print(f"   ❌ Transaction failed for Person {person_num}: {error_msg}")

                transactions.append({
                    "from": f"Person {person_num}",
                    "fromAddress": person_address,
                    "to": "Person 3",
                    "toAddress": person3_address,
                    "amount": amount,
                    "status": "failed",
                    "error": error_msg
                })

        print("\n✨ Payment execution complete!")

        return {
            "success": True,
            "transactions": transactions,
            "total_processed": len(transactions)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error executing payments: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error executing payments: {str(e)}"
        )

@app.get("/")
async def root():
    return {"message": "Locus Receipt Splitter API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
