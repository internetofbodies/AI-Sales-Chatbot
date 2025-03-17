from flask import Flask, request, jsonify, render_template, send_from_directory, url_for, session
import stripe
import openai
import os
import re

app = Flask(__name__, static_folder="static")
app.secret_key = "your_secret_key"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
stripe.api_key = STRIPE_API_KEY

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/reframer_payment")
def reframer_payment():
    return render_template("reframer_payment.html")

@app.route("/chatbot", methods=["POST"])
def chatbot():
    user_input = request.json.get("message").lower()

    # Flight detection pattern
    flight_pattern = r"flight from (.+?) to (.+?) on (.+)"
    match = re.search(flight_pattern, user_input)

    if match:
        departure = match.group(1).strip()
        destination = match.group(2).strip()
        date = match.group(3).strip()

        session["flight_details"] = {
            "airline": "AI Flights",
            "price": 250,
            "departure": departure.title(),
            "destination": destination.title(),
            "date": date
        }

        return jsonify({
            "response": f"✅ Flight found! {session['flight_details']['airline']} from {session['flight_details']['departure']} to {session['flight_details']['destination']} on {session['flight_details']['date']} for **${session['flight_details']['price']}**. Do you want to proceed with booking?"
        })

    # Handle booking confirmation
    if user_input in ["yes", "yes book my flight", "proceed with booking"]:
        flight_details = session.get("flight_details")
        if not flight_details:
            return jsonify({"response": "⚠️ I lost the flight details. Please search for a flight again."})

        return jsonify({
            "response": f"🎉 Great! Click **'Pay Now'** to complete your payment for {flight_details['airline']} from {flight_details['departure']} to {flight_details['destination']} on {flight_details['date']} for **${flight_details['price']}**.",
            "redirect_payment": True
        })

    # AI Assistant Response
    try:
        messages = session.get("conversation_history", [])
        messages.append({"role": "user", "content": user_input})

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )

        ai_response = response.choices[0].message.content
        messages.append({"role": "assistant", "content": ai_response})
        session["conversation_history"] = messages

        return jsonify({"response": ai_response})
    except Exception as e:
        return jsonify({"response": f"Error: {str(e)}"}), 500

@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    try:
        flight_details = session.get("flight_details")

        if not flight_details:
            return jsonify({"error": "Flight details missing. Please try booking again."}), 400

        amount = flight_details.get("price", 250) * 100
        if amount < 100:
            return jsonify({"error": "Invalid amount. Minimum amount is $1.00"}), 400

        stripe_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f"Flight from {flight_details['departure']} to {flight_details['destination']}",
                        'description': f"Airline: {flight_details['airline']}, Date: {flight_details['date']}"
                    },
                    'unit_amount': amount,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url="http://127.0.0.1:5000/success",
            cancel_url="http://127.0.0.1:5000/cancel",
        )

        return jsonify({"checkout_url": stripe_session.url})

    except stripe.error.StripeError as e:
        return jsonify({"error": "Stripe payment processing failed."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/success")
def success():
    return "Flight booking successful! Your ticket details will be emailed to you shortly."

@app.route("/cancel")
def cancel():
    return "Flight booking was canceled. You can try again."

@app.route("/confirmation")
def confirmation():
    return render_template("confirmation.html")

@app.route("/pay-now")
def pay_now():
    return render_template("reframer_payment.html")

if __name__ == "__main__":
    app.run(debug=True)
