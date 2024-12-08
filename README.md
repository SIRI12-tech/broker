# Bitcoin Broker Platform

A comprehensive Bitcoin trading platform built with Django and modern frontend technologies.

## Features

- User Authentication and Authorization
- Real-time Bitcoin Price Tracking
- Limit Orders
- Price Alerts
- Secure Trading Environment
- Responsive Design

## Tech Stack

- Backend: Django
- Frontend: HTML, Tailwind CSS, JavaScript
- Database: SQLite (development) / PostgreSQL (production)
- Authentication: Django Allauth
- API Integration: Binance API

## Setup Instructions

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Set up environment variables:
   - Create a `.env` file in the root directory
   - Add necessary environment variables (see .env.example)

5. Run migrations:
   ```
   python manage.py migrate
   ```
6. Start the development server:
   ```
   python manage.py runserver
   ```

## Security Features

- Secure password hashing
- CSRF protection
- XSS prevention
- Rate limiting
- Session security
- 2FA support

## API Documentation

Detailed API documentation can be found in the `/docs` directory.

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
