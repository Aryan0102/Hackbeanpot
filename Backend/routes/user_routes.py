# Imports
from flask import request, jsonify, session, request, redirect, url_for
from config import db
from models import * 
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, jwt_required
from flask import Blueprint
import random
import string
from bson.objectid import ObjectId, InvalidId


user_bp = Blueprint('user', __name__, url_prefix="/api/user")

# Set up bcrypt instance
bcrypt = Bcrypt()

"""
GET /api/user/getAllUser - Create a new user
POST /api/user/create - User Creation
POST /api/user/login - Log into current user
PUT /api/user/update - Update user profile
POST /api/user/getProfileInformation - Get specfic profile details
"""

"""
GET: /api/user/getAllUsers
Fetches all users from the database and returns them as a JSON response
"""
@user_bp.route('/getAllUsers', methods=["GET"])
def get_all_users():
    try:
        collection = db.users
        # Finds with no filers and id removed
        documents = list(collection.find({}, {"_id": 0}))
        return jsonify({"documents":documents, "success":True, "status":200})
    except Exception as e:
        return jsonify({"error": str(e), "status":500})


# Generates a random seed of length 15 for DiceBear profiles
def random_seed():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=15))

# Generates the actual image using the DiceBear API and random_seed function
def random_profile():
    try:
        seed = random_seed()
        return f'https://api.dicebear.com/9.x/shapes/png?seed={seed}&format=png'
    except Exception as e:
        print(f"Error: {e}")
        return "https://upload.wikimedia.org/wikipedia/commons/d/d2/Solid_white.png"

"""
POST: /api/user/create

{
    "email": ""
    "password": ""
    "user_name": ""
    "first_name": ""
    "last_name": ""
}

Creates a new user in the database
Returns a JWT of the user's ID
"""
@user_bp.route("/create", methods=["POST"])
def create_user():
    # Check to see if content-type is json
    if request.headers['Content-Type'] != 'application/json':
        return jsonify({"error": "Content-Type must be application/json", "success":False, "status":400})
    
    #Sets data from request
    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON", "success":False, "status":400})
    
    try:
        collection = db.users
        existing_user = collection.find_one({"email": data.get("email")})
        if existing_user:
            return jsonify({"error": "Email already exists", "success":False, "status": 409})

        # Generates encrypted password using bcrypt
        hashed_password = bcrypt.generate_password_hash(data.get('password')).decode('utf-8')
        #Create user using data
        user = User(
            email = data.get('email'),
            password = hashed_password,
            user_name = data.get('user_name'),
            first_name = data.get('first_name'),
            last_name = data.get('last_name'),
            profile_picture = random_profile(),
            created_at = datetime.datetime.now(),
            updated_at = datetime.datetime.now(),
            )
        user.save()

        #Create JWT token and return it
        token = create_access_token(identity=str(user.id))
        return jsonify({"message":"User Creation Successful", "success":True, "token":token, "status":200})
    except Exception as e:
        return jsonify({"error": str(e), "status":500})

"""
POST: /api/user/login

{
    "email": ""
    "password": ""
}

Checks if user exists and password is correct, logs them in
Returns a JWT of the user's ID
"""
@user_bp.route("/login", methods=["POST"])
def login():
    # Sets data from request
    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON", "success":False, "status":400})
    try:
        # Fetches email and password, fetches user from email
        email = data.get('email')
        password = data.get('password')
        user = User.objects(email=email).first()

        # Compare given and hashed password from database, if match, login
        if user and bcrypt.check_password_hash(user.password, password):
            token = create_access_token(identity=str(user.id))
            return jsonify({"message":"Login Successful", "success":True, "token":token, "status":200})
        else:
            return jsonify({"error": "Invalid Email or Password", "success":False, "status":401})
    except Exception as e:
        return jsonify({"error": str(e), "status":500})
    




"""
POST: /api/user/getProfileInformation
{
    "profileId": ""
}

Fetches the specific user information
Returns success, message, and data
"""
@user_bp.route('/getProfileInformation', methods=["POST"])
def get_profile_information():
    # Check to see if content-type is json
    if request.headers['Content-Type'] != 'application/json':
        return jsonify({"error": "Content-Type must be application/json", "success":False, "status":400})

    #Sets data from request
    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON", "success":False, "status": 400})

    try:
        # Try to convert the string profileId to an ObjectId type
        try:
            objID = ObjectId(data.get("profileId"))
        except InvalidId:
            return jsonify({"error": "Invalid ObjectId format", "success":False, "status": 400})

        profile = db.users.find_one({"_id": objID})

        if profile:
            # Remove certain fields from the profile
            exclude = ["_id", "password", "updated_at", "favorites", "settings"]
            for field in exclude:
                profile.pop(field, None)

            return jsonify({"message":"Fetched profile successfully", "success":True, "profile":profile, "status":200})
        else:
            return jsonify({"message":"Error Fetching Profile/Does Not Exist", "success":False, "status":400})
    except Exception as e:
        return jsonify({"error": str(e), "status":500})
    

"""
PUT: /api/user/create

{
    "profileId":""
    {key}:{value}
    ...
}

Updates a user in the database
Returns message and status code
"""
@user_bp.route("/update", methods=["PUT"])
def update_user():
    # Check to see if content-type is json
    if request.headers['Content-Type'] != 'application/json':
        return jsonify({"error": "Content-Type must be application/json", "success":False, "status":400})
    
    #Sets data from request
    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON", "success":False, "status":400})
    
    try:
        try:
            objID = ObjectId(data.get("profileId"))
        except InvalidId:
            return jsonify({"error": "Invalid ObjectId format", "success":False, "status": 400})

        profile = db.users.find_one({"_id": objID})

        if not profile:
            return jsonify({"error": "User not found", "success": False, "status": 404})

        for key in data:
            profile[key] = data[key]

        db.users.update_one({"_id": objID}, {"$set": profile})

        return jsonify({"message":"User Updated Successfully", "success":True, "status":200})
    except Exception as e:
        return jsonify({"error": str(e), "status":500})