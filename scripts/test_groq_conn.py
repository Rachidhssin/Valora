import os
import asyncio
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

def test_groq():
    print("🧪 Testing Groq API Connection...")
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ GROQ_API_KEY not found in .env")
        return

    print(f"🔑 Key found: {api_key[:8]}...")
    
    try:
        client = Groq(api_key=api_key)
        
        print("\n🚀 Sending test request (llama-3.1-8b-instant)...")
        completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": "Say 'Hello from Valora!' if you can hear me."
                }
            ],
            model="llama-3.1-8b-instant",
        )
        
        response = completion.choices[0].message.content
        print(f"\n✅ Response received:\n{response}")
        print("\nUsage stats should update in your dashboard shortly.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    test_groq()
