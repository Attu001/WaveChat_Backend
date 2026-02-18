WaveChat_Backend

Backend API for WaveChat, a real-time chat application built with Django. This project handles user authentication, chat messaging, and provides REST APIs for the frontend client.

Table of Contents

Features

Tech Stack

Project Structure

Installation

Running the Project

API Endpoints

Contributing

License

Features

User registration and authentication (JWT or token-based)

Chat rooms and private messaging

REST APIs for sending and receiving messages

User management

Ready for frontend integration (React/Flutter/etc.)

Tech Stack

Backend: Django, Django REST Framework

Database: SQLite (default)

Dependencies: Listed in requirements.txt

Optional: Django Channels for real-time messaging (if implemented)

Project Structure
WaveChat_Backend/
├── auth/                  # Authentication app
├── authorization/         # Role/permission management
├── chat/                  # Chat models and API views
├── wavechat/              # Django project settings
├── manage.py              # Django CLI commands
├── db.sqlite3             # SQLite database
├── requirements.txt       # Python dependencies
└── README.md

Installation

Clone the repository

git clone https://github.com/Attu001/WaveChat_Backend.git
cd WaveChat_Backend


Create a virtual environment

python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows


Install dependencies

pip install -r requirements.txt


Apply migrations

python manage.py migrate


Create superuser (optional, for admin access)

python manage.py createsuperuser

Running the Project

Start the development server:

python manage.py runserver


The backend will be available at: http://127.0.0.1:8000/

API Endpoints

(Example endpoints — adjust based on your actual implementation)

User Authentication

POST /api/auth/register/ – Register new user

POST /api/auth/login/ – Login user

POST /api/auth/logout/ – Logout user

Chat

GET /api/chat/rooms/ – Get list of chat rooms

POST /api/chat/message/ – Send a message

GET /api/chat/messages/<room_id>/ – Fetch messages from a room

Users

GET /api/users/ – Fetch all users

Contributing

Fork the repository

Create a new branch: git checkout -b feature-name

Make your changes

Commit: git commit -m "Add feature"

Push: git push origin feature-name

Open a Pull Request
