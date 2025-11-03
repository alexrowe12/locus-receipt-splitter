from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_mcp_m2m import MCPClientCredentials
from dotenv import load_dotenv
from pydantic import BaseModel
import base64
import io
import csv
import os
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

@app.get("/")
async def root():
    return {"message": "Locus Receipt Splitter API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
