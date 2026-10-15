🚌 Gouraw Bus Travels

A full-stack Bus Ticket Booking + Live Bus Tracking web application. Search buses between cities and villages, pick your seats, book tickets, and track the bus stop by stop.

🔗 Live Demo: https://panigouraw.github.io/Gouraw-Bus-Travels ⚙️ Backend API: https://gouraw-bus-api.onrender.com/docs

⏳ The backend runs on a free Render plan, so the first request after inactivity may take 30–60 seconds to wake up.

✨ Features
🔍 Search buses by From, To and journey date
📍 Live bus tracking with every stop on the route, including village names
💺 Seat selection with booked / available seats
🧑 Passenger details – name, age, gender, email, mobile
✅ Booking confirmation popup with ticket details
🚫 "Buses not available" modern popup when no buses match
🔐 Login / Signup for users
📜 Booking history for every user
❌ Ticket cancellation
🌍 India-wide demo routes (Kadapa, Tirupati, Bengaluru, Hyderabad, Chennai and more)
📱 Responsive design – works on mobile and desktop
🛠️ Tech Stack
Layer	Technology
Frontend	HTML5, CSS3, JavaScript
Backend	Python, FastAPI, Uvicorn
Database	MySQL
Hosting	GitHub Pages (frontend), Render (backend), Aiven (MySQL)
Tools	Git, GitHub, VS Code, Postman, MySQL Workbench
🗄️ Database Design

The MySQL database has 7 tables:

buses · routes · stops · schedules · bookings · passengers · bus_locations

📁 Project Structure
Bus-Ticket-Booking/
├── main.py              # FastAPI app and API endpoints
├── database.py          # Database connection setup
├── models.py            # Database table models
├── create_tables.py     # Creates all tables in MySQL
├── generate_india.py    # Generates demo routes, buses and stops
├── index.html           # Frontend
├── requirements.txt     # Python dependencies
└── README.md
🚀 Run Locally
1. Clone the repository
bash
git clone https://github.com/panigouraw/Gouraw-Bus-Travels.git
cd Gouraw-Bus-Travels
2. Create a virtual environment
bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac / Linux
3. Install dependencies
bash
pip install -r requirements.txt
4. Set up MySQL

Create a database in MySQL:

sql
CREATE DATABASE bus_booking;

Then set your connection string as an environment variable (or in database.py for local use):

DATABASE_URL=mysql+pymysql://USER:PASSWORD@localhost:3306/bus_booking
5. Create tables and demo data
bash
python create_tables.py
python generate_india.py
6. Start the backend
bash
uvicorn main:app --reload

API docs will be available at http://127.0.0.1:8000/docs

7. Open the frontend

Open index.html in your browser (or use the VS Code Live Server extension).

🔌 API Overview
Purpose	Description
Search buses	Find buses by from, to and date
Seats	Get seat availability for a schedule
Book ticket	Create a booking with passenger details
Booking lookup	Fetch a booking / ticket
Live tracking	Get current bus location and upcoming stops
Signup / Login	User authentication
Booking history	List a user's past bookings
Cancel booking	Cancel an existing ticket

Full interactive documentation is available at /docs (Swagger UI).

☁️ Deployment
Frontend: GitHub Pages
Backend: Render (FastAPI)
Database: Aiven (MySQL)

Environment variable required on Render:

DATABASE_URL=<your Aiven MySQL connection string>
🔮 Future Improvements
🗺️ Live map view for bus tracking
💳 Online payment integration
📧 Email / SMS ticket confirmation
🧾 Downloadable PDF ticket
📸 Screenshots

Add screenshots of the home page, seat selection, booking confirmation and live tracking here.

![Home](screenshots/home.png)
![Seat Selection](screenshots/seats.png)
👨‍💻 Author

Pani Gouraw Kalisetty B.Tech – Artificial Intelligence & Data Science

🌐 Portfolio: https://panigouraw.github.io/
💻 GitHub: https://github.com/panigouraw

⭐ If you like this project, give it a star!
