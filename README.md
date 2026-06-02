# 🚀 Integrated Customer Relationship Management System (Wallex CRM)

This project is a powerful and dynamic system for managing tickets, team workspaces, and designing workflows, which integrates seamlessly with the **Zammad** ticketing system.

## ✨ Key Features
* **Advanced Authentication:** Secure login system based on JWT with Two-Factor Authentication (2FA / Google Authenticator).
* **Dynamic Form Builder Engine (EAV):** Ability to define dynamic fields for each category without needing to alter the database schema.
* **Workflow Engine:** Visual design of conditional paths and automated actions.
* **Live Synchronization:** Automatic sync of users and teams with the Zammad ticketing system.
* **Modern UI:** Full support for Dark/Light mode using Tailwind v4 and smooth animations with Framer Motion.

---

## 🛠 Technologies Used

**Backend:**
* Python 3.10+
* Django & Django REST Framework
* SimpleJWT & PyOTP (For security and tokens)
* SQLite / PostgreSQL

**Frontend:**
* Next.js 14+ (App Router)
* React Hook Form
* Tailwind CSS v4
* Framer Motion & Lucide Icons

---

## ⚙️ Prerequisites
Before running the project, ensure you have the following tools installed on your system:
* [Python](https://www.python.org/downloads/) (Version 3.10 or higher)
* [Node.js](https://nodejs.org/en/) (Version 18 or higher)
* [Docker & Docker Compose](https://www.docker.com/) (Required for running Zammad locally without headaches)

---

## 🚀 Installation and Setup Guide

### 1. Foolproof Zammad Setup (Ticketing Core)

Since this CRM acts as a smart wrapper around Zammad, you **must** have a Zammad instance running. Setting it up manually can be tricky, so we strongly recommend using Docker Compose for local development. Follow these exact steps:

**Step 1.1: Run Zammad via Docker**
Open a terminal and run the following commands to spin up Zammad:

```bash
# Clone the official Zammad Docker Compose repository
git clone [https://github.com/zammad/zammad-docker-compose.git](https://github.com/zammad/zammad-docker-compose.git)
cd zammad-docker-compose

# ⚠️ CRITICAL STEP FOR ELASTICSEARCH ⚠️
# If you are on Linux, macOS, or Windows WSL2, you MUST run this command,
# otherwise the Zammad container will silently crash and fail to start:
sudo sysctl -w vm.max_map_count=262144

# Start the Zammad containers in the background
docker-compose up -d
```

## Step 1.2: The Initial Wizard (Skip the Email Setup!)

* Wait about 2 to 5 minutes for all databases and services to initialize.

* Open your browser and go to: http://localhost:8080.

* You will see the Zammad Welcome screen. Click on "Set up new system".

* Admin Account: Fill in your details (Name, Email, Password) to create the main Zammad admin.

* Organization: Enter a dummy organization name (e.g., "Wallex CRM Local").

* Email Notification: 🚨 IMPORTANT: When asked to configure an email channel, click "Skip" at the bottom of the screen. You do not need email configuration for local API development.

## Step 1.3: Generate the API Token
Now that you are inside the Zammad dashboard:

* Click on your profile picture (bottom left corner) and select Profile.

* Navigate to Token Access in the left menu and click Create.

* Name it "CRM Backend".

* Check the permissions for admin, ticket, user, and group.

* Click submit and copy the generated token. Keep it safe; you will need it for the Django backend.

2. Backend Setup (Django)
Open a new terminal and navigate to the backend folder (crm-back):

# Create a virtual environment
```` bash
python -m venv .venv
````
# Activate the virtual environment
# On macOS/Linux:
```` bash
source .venv/bin/activate
````
# On Windows:
```` bash
.venv\\Scripts\\activate
````

# Install required packages
```` bash
pip install -r requirements.txt
````
# Create and apply database migrations
```` bash
python manage.py makemigrations
python manage.py migrate
````
# Create a superuser (Admin account for the CRM)
```` bash
python manage.py createsuperuser
Step 2.1: Connect Backend to Zammad
Inside the crm-back folder, create a file named .env and add the token you got from Step 1.3:
````
## Zammad Configuration
ZAMMAD_URL=http://localhost:8080
ZAMMAD_API_TOKEN=paste_your_copied_zammad_token_here
Step 2.2: Add Base Actions & Run


## Run the backend server
````bash
python manage.py runserver
````
Important Note for Initial Data: For the workflow engine to function correctly, you must add the base actions to the database. Open a new terminal, activate the .venv, run python manage.py shell, and execute the python script that generates ActionDefinition records.

3. Frontend Setup (Next.js)
Open a new terminal and navigate to the frontend folder:


## Install project dependencies
````bash
npm install
````

## Create environment variables file
````bash
cp .env.example .env.local
````
Open .env.local and ensure it points to your Django backend:

Code snippet
NEXT_PUBLIC_API_BASE_URL=[http://127.0.0.1:8000/api](http://127.0.0.1:8000/api)
## Start the Next.js development server
````bash
npm run dev
````
### 💻 How to UseOnce all 3 parts (Zammad, Django, Next.js) are running:

Open your browser and navigate to http://localhost:3000.

Log in using the superuser credentials you created in Step 2.

Go to Settings > Workflow Engine to ensure your actions are loaded.

Go to Settings > Users / Teams to create agents and workspaces. They will instantly sync with your local Zammad instance!