import math
from flask import request, jsonify, Blueprint
import openai
import random
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from models import *
from .navigation_routes import routes_with_landmarks
from config import OPENAI_SECRET_KEY

# Set up post blueprint at "/api/quests"
quests_bp = Blueprint('quests', __name__, url_prefix="/api/quests")

@quests_bp.route('/generateFromRoute', methods=['POST'])
def generate_quests_from_route():

    """
    Uses a JSON containing:
    {
       "start_location": "Location A",
       "end_location": "Location B",
       "route_summary": "Summary text...",
       "route_steps": "Step by step directions...",
       "total_distance": "120 miles",
       "total_duration": "2 hours",
       "landmarks": [
           {
             "name": "Landmark 1",
             "type": "historical",
             "rating": 4.5,
             "latitude": 40.7128,
             "longitude": -74.0060
           },
           {
             "name": "Landmark 2",
             "type": "restaurant",
             "rating": 4.0
           },
           ... more landmarks ...
       ]
    }

    For each landmark, a quest is generated by calling ChatGPT.
    Returns the list of created quests.
    """

    if request.headers.get("Content-Type") != "application/json":
        return jsonify({"error": "Content-Type must be application/json", "success": False, "status": 400})
    
    data = request.get_json()
    start_location = data.get("start_location")
    end_location = data.get("end_location")

    if not start_location or not end_location:
        return jsonify({"error": "No start or end", "success": False, "status": 400})

    route_info = routes_with_landmarks(start_location, end_location)
    required_fields = ["start_location", "end_location", "route_summary", "route_steps", "total_distance", "total_duration", "landmarks"]

    if "error" in route_info:
        return jsonify(route_info)

    for field in required_fields:
        if field not in route_info:
            return jsonify({"error": f"Missing required field: {field}", "success": False, "status": 400})

    landmarks = route_info.get("landmarks", [])

    quests_created = []
    for landmark in landmarks:
        # Generate quest details using ChatGPT
        quest_details = generate_quest_via_chatgpt(landmark)
        landmark_address = landmark.get("address", "Unknown Address")

        try:
            quest = Quest(
                name = quest_details.get("name"),
                description = quest_details.get("description"),
                landmark = landmark.get("name"),
                reward = quest_details.get("reward"),
                address = landmark_address
            )
            quest.save()
            quests_created.append(quest.to_json())
        except Exception as e:
            return jsonify({"error": f"Error saving quest: {str(e)}", "success": False, "status": 500})
        
    return jsonify({
        "message": "Quests generated successfully",
        "quests": quests_created,
        "success": True,
        "status": 201
    })


def generate_quest_via_chatgpt(landmark):
    """
    Uses OpenAI API to generate a unique quest for a given landmark.
    Returns a dictionary with keys: "name", "description", "reward".
    """
    
    openai.api_key = OPENAI_SECRET_KEY
    client = openai.OpenAI(api_key=OPENAI_SECRET_KEY)

    landmark_name = landmark.get("name", "Unknown Location")
    landmark_type = ", ".join(landmark.get("type", []))  # Join all types as string
    location = f"({landmark.get('latitude', 'unknown')}, {landmark.get('longitude', 'unknown')})"

    # Define possible challenges based on landmark type
    prompt = f"""

    You are an expert at designing fun and engaging travel quests. 
    Create a unique challenge for someone visiting {landmark_name}, which is a {landmark_type} located at {location}. 
    Make the challenge specific to this landmark and engaging for travelers.

    Keep it short, no more than 15/20 words max

    Example challenges
    
        If it is a museum, any of the following are good
            "Take a guided tour.",
            "Find a piece of art that you like the most, and take a picture with it.",
            "Collect a museum brochure and find one fact that most visitors don’t know about the exhibits.",
            "Spend at least 30 minutes at the museum, and try to describe your favorite artwork or artifact to someone else."
        
        If it is a restaurant, any of the following are good
            "Order a signature dish from the restaurant and take a picture of your meal before eating.",
            "Talk to the staff about the most popular dish and try it out.",
            "Leave a positive review or recommendation about the restaurant on a food review app or social media.",
            "Try a dish you’ve never had before and rate it from 1 to 10."
        
        If it is a university, any of the following are good
            "Buy a school souvenir or piece of merchandise like a T-shirt or mug from the campus store.",
            "Take a picture at the main campus entrance with a campus map or university flag.",
            "Visit the campus library and find an interesting book or historical document to look at.",
            "Sit on the campus quad and do something productive (like reading or journaling) for 15 minutes."
        
        If it is a shopping mall, any of the following are good
            "Buy something you’ve never bought before from a store you’ve never visited.",
            "Find a sale and make a purchase from a store that has something you’ve been eyeing.",
            "Take a photo of your favorite store in the mall and show it to a friend to ask if they’ve been there.",
            "Spend 15 minutes walking around the mall without buying anything and just window shop."
        
        If it is a historical place, any of the following are good
            "Take a selfie with the landmark in the background.",
            "Read a historical fact about the landmark and explain it to someone visiting with you.",
            "Find the oldest part of the landmark and take a close-up photo of it.",
            "Look for a plaque or a sign near the landmark that gives historical context and take a photo of it."
        
        If it is a park, any of the following are good
            "Walk at least one mile in the park and take a picture of your favorite spot.",
            "Find and identify at least three different types of trees or plants.",
            "Sit on a bench for 10 minutes and sketch something you see in the park.",
            "Have a small picnic and enjoy the nature around you."
        
        If it is a amusement park, any of the following are good
            "Ride at least one roller coaster and take a photo from the top if allowed.",
            "Win a prize from a carnival game and show it off in a selfie.",
            "Eat a classic amusement park food item and rate it out of 10.",
            "Find the tallest ride in the park and take a picture of it."
        
        If it is a library, any of the following are good
            "Find a book with a title that starts with the same letter as your name.",
            "Read at least one page of a random book and summarize it in one sentence.",
            "Take a picture of the most interesting book cover you find.",
            "Sit in the reading area for 10 minutes and read quietly."
        
        You are not restricted to these, makes others following similar guides
    """
    
    messages=[{"role": "system", "content": "You are a helpful assistant that creates travel challenges."},
                {"role": "user", "content": prompt}],

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # or "gpt-3.5-turbo gpt-4"
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates travel challenges."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        # Extract response
        challenge = response.choices[0].message.content

    except Exception as e:
        print(f"OpenAI API error: {e}")
        challenge = "Explore this location and take a unique photo!"

    return {
        "name": f"Quest at {landmark.get('name')}",
        "description": f"Visit {landmark.get('name')} and complete the challenge: {challenge}",
        "reward": math.floor(random.randint(100, 300) / 10) * 10
    }