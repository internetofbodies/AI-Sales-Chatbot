from flask import Flask, request, jsonify, render_template
import stripe
import openai  # OpenAI API for AI responses
import os

app = Flask(__name__)

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Uses environment variable
openai.api_key = OPENAI_API_KEY

# Stripe API Key
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")  # Uses environment variable
stripe.api_key = STRIPE_API_KEY

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chatbot", methods=["POST"])
def chatbot():
    user_input = request.json.get("message").lower()

    # Predefined responses for services
    if "logo" in user_input:
        if "minimalist" in user_input:
            style = "minimalist"
        elif "modern" in user_input:
            style = "modern"
        elif "colorful" in user_input:
            style = "colorful"
        else:
            return jsonify({"response": "Would you like a minimalist, modern, or colorful logo?"})

        # Generate logo using DALL·E
        try:
            dalle_response = openai.images.generate(
                model="dall-e-3",
                prompt=f"A {style} business logo, high resolution, professional.",
                size="1024x1024",  # ✅ Fix: Use a valid size
                n=1
            )

            image_url = dalle_response.data[0].url
            return jsonify({"response": f"Here is your {style} logo:", "image_url": image_url})
        except Exception as e:
            return jsonify({"response": f"Error generating logo: {str(e)}"}), 500

    if "website" in user_input:
        if "business" in user_input:
            website_type = "business"
        elif "e-commerce" in user_input:
            website_type = "e-commerce"
        else:
            return jsonify({"response": "Do you want a business website or an e-commerce site?"})

        # Generate a simple website template
        try:
            response = openai.chat.completions.create(  # ✅ Fix: Use correct API call
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"Generate a simple HTML template for a {website_type} website."}
                ]
            )
            html_code = response.choices[0].message.content
            return jsonify({"response": f"Here is your {website_type} website:", "html_code": html_code})
        except Exception as e:
            return jsonify({"response": f"Error generating website: {str(e)}"}), 500

    # AI Response using OpenAI API
    try:
        response = openai.chat.completions.create(  # ✅ Fix: Use correct API call
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a sales assistant for AI-generated services."},
                {"role": "user", "content": user_input}
            ]
        )
        return jsonify({"response": response.choices[0].message.content})
    except Exception as e:
        return jsonify({"response": f"Error: {str(e)}"}), 500

    # Payment API for Admin to Customize Payment
@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    data = request.json
    amount = data.get("amount")  # Amount should be provided by the admin

    if not amount or amount < 100:  # Stripe requires the amount in cents (e.g., $1.00 = 100 cents)
        return jsonify({"error": "Invalid amount. Minimum amount is $1.00"}), 400

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': 'AI Service'},
                    'unit_amount': amount,  # Admin-defined amount
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url="https://ai-sales-chatbot.onrender.com/success",
            cancel_url="https://ai-sales-chatbot.onrender.com/cancel",
        )

        return jsonify({"checkout_url": session.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Success Page Route
@app.route("/success")
def success():
    return "Payment Successful! Thank you for your purchase."

# Cancel Page Route
@app.route("/cancel")
def cancel():
    return "Payment Canceled. Please try again."

if __name__ == "__main__":
    app.run(debug=True)
