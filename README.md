
# SafeRoute — Pothole and Road Damage Reporting System

## About the Project
SafeRoute is a web-based road damage reporting system
developed as a B.Tech academic project.

The application allows users to report potholes and
damaged roads, select affected locations, upload
photographs, and track report status.

## Problem Statement
Potholes and damaged roads create safety risks for
drivers and pedestrians. SafeRoute aims to simplify
the process of reporting road damage and tracking
complaints.

## Technologies Used
- Python
- Flask
- SQLite
- HTML
- CSS

## Features
- Submit pothole and road damage reports
- Select road damage locations using map coordinates
- Upload photographs of damaged roads
- View submitted reports
- Track reports using a report ID
- Administrator login
- Update report status
- Admin dashboard with basic usage statistics

## Project Structure
SafeRoute/
  app.py
  requirements.txt
  templates/
  static/
  README.md

## Installation
1. Clone the repository.
2. Install dependencies:

   pip install -r requirements.txt

3. Configure the ROADWATCH_SECRET_KEY and
   ROADWATCH_ADMIN_PASSWORD environment variables.

4. Run the application:

   python app.py

5. Open http://127.0.0.1:5000

## Research and Objectives
The project focuses on understanding road damage
reporting challenges and exploring how a web-based
system can simplify reporting and tracking.

## Future Improvements
- Improve report verification
- Add automated road damage classification
- Improve location-based analysis
- Enhance reporting analytics

## Project Status
Academic project — ongoing development and testing.
