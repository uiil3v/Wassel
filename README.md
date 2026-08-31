# Wassel - Smart Transportation Platform for University Students

Wassel is a graduation project built with Django. It is a web-based platform that organizes daily student transportation by connecting students with independent drivers who provide regular transportation services through subscriptions.

The platform focuses on making transportation safer, clearer, and more organized. Students can browse available subscriptions by city, neighborhood, price, and driver rating, while drivers can create subscriptions and manage student requests. Administrators can supervise the platform, verify drivers, monitor payments, send notifications, and handle support tickets.

## Project Idea

Many students face difficulties finding a stable, safe, and affordable daily transportation option. At the same time, independent drivers often struggle to reach students who need regular transportation. Wassel provides a digital solution that connects both sides in one organized platform using subscriptions, driver verification, digital wallets, notifications, reviews, and electronic contracts.

## User Roles

- Guest: Can browse public pages, drivers, and available subscriptions.
- Student: Can create an account, complete a profile, browse subscriptions, submit subscription requests, pay using the wallet, track requests, view contracts, and receive notifications.
- Driver: Can complete a profile, upload verification documents, wait for admin approval, create subscriptions, manage student requests, and track earnings.
- Admin: Can manage users, approve or reject drivers, monitor subscriptions and requests, track payments, send notifications, and manage support tickets.

## Main Features

- Role-based registration and login.
- Email verification before account usage.
- Separate profiles for students and drivers.
- Driver verification using identity, driving license, and vehicle documents.
- Driver and subscription browsing with filters.
- Monthly and semester-based subscriptions.
- Student subscription requests with weekly pickup and return schedules.
- Digital wallet for every user.
- Freezing the subscription amount when a student submits a request.
- Transferring payment to the driver after approval with platform commission.
- Refund handling for rejected or cancelled requests.
- Automatic electronic contract creation after request approval.
- Contract download as PDF.
- In-platform notifications.
- Email notifications for important events.
- Reviews between students and drivers after subscription completion.
- Support ticket system with email verification code.
- Admin dashboard for platform management and statistics.
- CSV export for wallet and payment records.

## Technologies

- Python
- Django
- SQLite for local development
- PostgreSQL support through `DATABASE_URL`
- Bootstrap RTL
- Bootstrap Icons
- Cloudinary for uploaded images and attachments
- WhiteNoise for static files
- WeasyPrint for PDF generation
- Django templates

## Project Structure

```text
Wassel/
├── Wassel/              # Main project settings
├── accounts/            # Users, authentication, email verification, and account recovery
├── admin_panel/         # Admin dashboard, reports, and management pages
├── contracts/           # Electronic contracts and PDF generation
├── driver/              # Driver dashboard, verification, subscriptions, and requests
├── location/            # Cities used for registration and filtering
├── main/                # Public pages and public browsing
├── notifications/       # System notifications
├── payment/             # Wallets, financial transactions, and commissions
├── reviews/             # Ratings and average rating updates
├── student/             # Student dashboard, requests, schedules, and profile
├── subscriptions/       # Subscriptions, subscription requests, and weekly schedules
├── support/             # Support tickets and ticket conversations
├── templates/           # Shared templates and email templates
├── static/              # Static files and images
├── manage.py
└── requirements.txt
```

## Requirements

- Python 3.11 or later
- pip
- Python virtual environment
- Cloudinary account for image and file uploads
- SMTP email account for email notifications

## Local Setup

1. Go to the project directory:

```bash
cd Wassel
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file inside the `Wassel` directory and add the required values:

```env
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-password
CLOUD_NAME=your-cloudinary-cloud-name
API_KEY=your-cloudinary-api-key
API_SECRET=your-cloudinary-api-secret
```

5. Apply database migrations:

```bash
python manage.py migrate
```

6. Create an admin account:

```bash
python manage.py createsuperuser
```

7. Start the development server:

```bash
python manage.py runserver
```

Then open:

```text
http://127.0.0.1:8000/
```

## Main Routes

- Home page: `/`
- Register: `/accounts/register/`
- Login: `/accounts/login/`
- Browse drivers: `/drivers/`
- Browse subscriptions: `/subscriptions/`
- Student dashboard: `/student/dashboard/`
- Driver dashboard: `/driver/dashboard/`
- Wallet: `/wallet/`
- Contracts: `/contracts/`
- Support: `/support/contact/`
- Admin panel: `/admin-panel/`
- Django admin: `/admin/`

## Payment Flow

The platform uses a digital wallet for each user:

1. The student deposits money into the wallet.
2. When the student submits a subscription request, the subscription amount is frozen.
3. If the driver rejects the request, the frozen amount is refunded to the student.
4. If the driver approves the request, 95% of the amount is transferred to the driver.
5. The platform keeps a 5% commission.
6. If an approved subscription is cancelled, the refund is calculated based on the remaining subscription period.

## Subscription Flow

1. The driver completes the profile and uploads verification documents.
2. The admin reviews the driver account and approves or rejects it.
3. After approval, the driver creates a subscription.
4. The student browses subscriptions and submits a request with a weekly schedule.
5. The system freezes the subscription amount.
6. The driver approves or rejects the request.
7. After approval, the system creates an electronic contract between the student and the driver.

## Admin Panel

The admin panel provides tools to monitor and manage:

- Users, students, and drivers.
- Subscription requests.
- Driver verification requests.
- Active, full, inactive, and expired subscriptions.
- Payments, commissions, refunds, and withdrawals.
- Sent notifications.
- Support tickets.
- Website visits.

## Important Notes

- Drivers cannot create or manage subscriptions before account approval.
- Students cannot submit subscription requests before completing their profiles.
- A student cannot have more than one active or pending subscription request at the same time.
- Drivers cannot edit a subscription after it receives student requests.
- Reviews are available only after the subscription ends.
- Some admin pages, such as payments, are restricted to the highest admin level.

## Project Check

Run the Django system check:

```bash
python manage.py check
```

Run tests:

```bash
python manage.py test
```

## Project Status

Wassel represents a functional version of the proposed smart transportation platform. It covers the core graduation project requirements, including authentication, user roles, subscriptions, requests, wallets, payments, contracts, notifications, reviews, support tickets, and admin management.

