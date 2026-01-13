# Battery Shop Management System

This is a Streamlit-based web application designed to manage battery inventory, warranty claims, service tracking, and stock loans for an Exide Care dealer.

## Features

*   **Dashboard**: View key metrics like total customers, active batteries, and service exchanges. Manage active service requests (pending/ready for pickup).
*   **Service & Warranty**:
    *   **New Warranty Claim**: Verify warranty status, send OTPs to customers, and process replacements or service requests. Generates professional HTML receipts.
    *   **Customer Pickup**: Manage returns of serviced batteries to customers with OTP verification.
*   **Search History**: Look up battery details and service history by Serial Number or Customer Phone.
*   **Stock Loan Exide**: Track stock requested from the Exide factory and audit received stock.
*   **Authentication**: Secure login system using Streamlit Secrets.

## Project Structure

The project follows a modular structure for better maintainability and separation of concerns:

*   `main.py`: The entry point of the application. Handles the UI layout and page navigation.
*   `models.py`: Defines the database schema using SQLAlchemy ORM (Customer, Battery, Exchange).
*   `database.py`: Manages database connections and session creation.
*   `services.py`: Contains the business logic and data access layer (CRUD operations).
*   `auth.py`: Handles user authentication logic.
*   `config.py`: Centralized configuration for constants and secrets retrieval.
*   `reset_db.py`: A utility script to reset or initialize the database schema.
*   `requirements.txt`: Lists the Python dependencies.

## How to Run Locally

1.  **Prerequisites**: Ensure you have Python installed.
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configuration**:
    Create a `.streamlit/secrets.toml` file in the project root with the following content (replace with your actual DB URL):
    ```toml
    DB_URL = "postgresql://user:password@host:port/dbname"
    ADMIN_USER = "admin"
    ADMIN_PASSWORD = "yourpassword"
    ```
    *Note: For local testing with SQLite, you can use `sqlite:///battery_shop.db` as the DB_URL.*

4.  **Run the App**:
    ```bash
    streamlit run main.py
    ```

## Deploying Updates to Streamlit Cloud

This app is deployed on Streamlit Cloud. To update the live application, you need to commit and push your changes to the connected Git repository.

### Steps to Update:

1.  **Stage Changes**:
    Add the modified files to the staging area.
    ```bash
    git add .
    ```

2.  **Commit Changes**:
    Save your changes with a descriptive message.
    ```bash
    git commit -m "Refactored codebase to use ORM and modular structure"
    ```

3.  **Push to Remote**:
    Upload your changes to GitHub (or your Git provider). Streamlit Cloud will automatically detect the new commit and redeploy the app.
    ```bash
    git push origin main
    ```

### Troubleshooting Deployment

*   If the app doesn't update immediately, check your Streamlit Cloud dashboard for build logs.
*   Ensure you have set up the `DB_URL`, `ADMIN_USER`, and `ADMIN_PASSWORD` in the Streamlit Cloud "Secrets" settings.
