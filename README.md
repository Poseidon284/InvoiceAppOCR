## Setup

1. Create virtual environment
   python -m venv venv
   source venv/bin/activate  (Windows: venv\Scripts\activate)

2. Install dependencies
   pip install -r requirements.txt

3. Create .env file
   POSTGRES_DB_URI=postgresql://<username>:<password>@<host>:<port>/<db>
   GOOGLE_API_KEY=your_api_key

4. Run application
   python app.py

5. Open browser
   http://127.0.0.1:5000/
