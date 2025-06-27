from flask import Flask, request, jsonify
import openai
import json
import os
import re
from datetime import datetime

app = Flask(__name__)
client = openai.OpenAI(api_key="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")

BOOKINGS_FILE = "bookings.json"

SYSTEM_PROMPT = """
You are a helpful theater ticket assistant for the Palation Theater.
You support booking, cancellation, and answering questions about performances.

Booking
For a booking to proceed, you must collect:
1. The name of the play (Dracula or Electra)
2. The time of the show (5pm or 9pm)
3. The number of tickets
Do NOT proceed with a booking unless all 3 are provided.
Once you have all the information, ask the user to confirm before proceeding with the booking. Do not complete the booking unless the user explicitly confirms.

Information
Apollo Stage – Overview
The Apollo Stage is one of the most modern venues at Palation Theater.
It hosts contemporary plays, with a focus on youth productions and experimental works.
It features 150 seats and a fully equipped lighting and sound system.
This period hosts "Dracula ".
The stage is versatile—ideal for dramas, musicals, and performance art.
Located on the 2nd floor of the theater building.
Shows change weekly, offering a fresh experience every time.
Fully accessible for people with mobility needs.
Collaborates with emerging directors and artists.
Entry is via the main staircase or elevator.
For details and bookings, contact the ticket office or use the chatbot.

The Main Stage – Overview
The Main Stage is the central and largest venue of the Palation Theater.
It hosts major theatrical productions, classical plays, and important premieres.
With 150 seats ,this period hosts "Electra", it features impressive architecture and stage design.
Equipped with advanced stage mechanics, lighting, and sound systems.
Ideal for large-scale shows with big casts and elaborate sets.
The hall's acoustics are excellent for drama and musical theater.
Located on the ground floor with direct access from the main entrance.
Welcomes hundreds of spectators and school groups every season.
Fully accessible with dedicated wheelchair seating areas.
It stands at the heart of the theater’s cultural activity.

Electra – Play Overview
Electra is a powerful ancient Greek tragedy by Sophocles.
It tells the gripping story of Electra, a woman consumed by grief and the desire for revenge after the murder of her father, King Agamemnon.
Set in a dark and emotional atmosphere, the play explores justice, fate, and family loyalty.
The performance at Palation Theater stays true to the classical roots while adding modern visual elements.
It features intense monologues, dynamic staging, and dramatic music.
Electra is staged in Main Stage  and is available at 5pm and 9pm daily.
The cast includes acclaimed Greek actors with experience in classical drama.
Subtitles or summaries are provided in English upon request.
It is recommended for audiences who enjoy deep emotional performances and timeless moral dilemmas.

Dracula – Play Overview
Dracula is a thrilling gothic horror adaptation based on Bram Stoker’s iconic novel.
The play follows Count Dracula’s eerie journey from Transylvania to Victorian London.
It blends suspense, romance, and supernatural mystery into a captivating performance.
Dark lighting, dramatic effects, and haunting music immerse the audience in the atmosphere.
The production features original costumes and carefully choreographed stage combat.
Performed in Apollo Stage, it’s ideal for fans of horror and classic literature.
Suitable for ages 13+, due to intense scenes and visual effects.
Shows are available daily at 5pm and 9pm.
English subtitles or narration available on request.
A timeless tale of fear, desire, and the unknown, brought vividly to life on stage.

After completing any task(booking,cancellation) or providing information, always end your message with a polite prompt such as:
"Can I help you with anything else? You can ask about bookings, cancellations, or performance information."

"""
# Capacities per stage
ROOM_CAPACITY = {
    "Dracula-5pm": 200,
    "Dracula-9pm": 200,
    "Electra-5pm": 150,
    "Electra-9pm": 150
}
def get_booked_tickets(play, time):
    return sum(b["tickets"] for b in load_bookings() if b["play"].lower() == play.lower() and b["time"] == time)


def load_bookings():
    if os.path.exists(BOOKINGS_FILE):
        with open(BOOKINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_bookings(bookings):
    with open(BOOKINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(bookings, f, indent=2)

def save_booking(play, time, tickets):
    bookings = load_bookings()
    bookings.append({
        "play": play,
        "time": time,
        "tickets": tickets
        #"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_bookings(bookings)

def delete_booking(play, time, tickets):
    bookings = load_bookings()
    for i, booking in enumerate(bookings):
        if booking["play"].lower() == play.lower() and booking["time"] == time and booking["tickets"] == tickets:
            del bookings[i]
            save_bookings(bookings)
            return True
    return False

@app.route("/book", methods=["POST"])
def book():
    try:
        data = request.json
        play = data.get("play")
        time = data.get("time")
        tickets = data.get("tickets")

        if not play or not time or not tickets:
            return jsonify({"error": "Missing data"}), 400

        room_key = f"{play}-{time}"
        capacity = ROOM_CAPACITY.get(room_key)
        if capacity is None:
            return jsonify({"error": "Invalid room/time"}), 400

        current = get_booked_tickets(play, time)
        print(f"{current} *************************************")
        print(capacity)
        if current + tickets > capacity:
            return jsonify({"error": f"Not enough available seats. Only {capacity - current} left."}), 400

        save_booking(play, time, tickets)
        #return jsonify({"result": "Booking completed."})
        return jsonify({
            "result": f"Thank you for confirming. Your booking for {tickets} tickets to '{play}' at {time} has been successfully processed."
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "").strip()
    history = request.json.get("history", [])
    
    if not user_input:
        return jsonify({"response": "Hello! How can I assist you with your theater booking today?"})

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
    messages.append({"role": "user", "content": user_input})

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=300,
            temperature=0.7,
        )

        reply = response.choices[0].message.content
        # 👉 ΔΕΝ καλούμε πλέον save_booking εδώ
        return jsonify({"response": reply})
        """
        play_match = re.search(r"\b(Dracula|Electra)\b", reply)
        time_match = re.search(r"\b(5pm|9pm)\b", reply)
        tickets_match = re.search(r"\b(\d+)\s*ticket", reply)

        confirmation_keywords = ["confirm", "booking made", "i'll confirm", "confirmed", "proceed"]

        is_confirmed = any(keyword in reply.lower() for keyword in confirmation_keywords)

        if is_confirmed and play_match and time_match and tickets_match:
            play = play_match.group(1)
            time = time_match.group(1)
            tickets = int(tickets_match.group(1))
            save_booking(play, time, tickets)

        return jsonify({"response": reply})
        """
    except openai.RateLimitError:
        return jsonify({"response": "⚠️ Server is temporarily unavailable. Please try again later."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/bookings", methods=["GET"])
def get_bookings():
    return jsonify(load_bookings())

@app.route("/cancel", methods=["POST"])
def cancel_booking():
    data = request.json
    play = data.get("play")
    time = data.get("time")
    tickets = data.get("tickets")

    if delete_booking(play, time, tickets):
        return jsonify({"result": "Booking cancelled"})
    return jsonify({"error": "Booking not found"}), 404

if __name__ == "__main__":
    app.run(debug=True, port=5000)
