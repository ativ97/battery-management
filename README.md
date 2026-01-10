# Battery Shop Management System

This is a Streamlit-based web application designed to manage battery inventory, warranty claims, service tracking, and stock loans for an Exide Care dealer.

## Features

*   **Dashboard**: View key metrics like total customers, active batteries, and service exchanges. Manage active service requests (pending/ready for pickup).
*   **Service & Warranty**:
    *   **New Warranty Claim**: Verify warranty status, send OTPs to customers, and process replacements or service requests. Generates professional HTML receipts.
    *   **Customer Pickup**: Manage returns of serviced batteries to customers with OTP verification.
*   **Search History**: Look up battery details and service history by Serial Number or Customer Phone.
*   **Stock Loan Exide**: Track stock requested from the Exide factory and audit received stock.
*   **Authentication**: Simple file-based login system.

## Project Structure

*   `main.py`: The main application file containing all the Streamlit UI logic, database interactions, and business logic.
*   `reset_db.py`: A utility script to reset or initialize the SQLite database (`battery_shop.db`).
*   `credentials.txt`: Stores the admin credentials (format: `username,password`).
*   `battery_shop.db`: The SQLite database file storing customers, batteries, and exchange logs.

## How to Run Locally

1.  **Prerequisites**: Ensure you have Python installed.
2.  **Install Dependencies**:
    ```bash
    pip install streamlit pandas
    ```
3.  **Run the App**:
    ```bash
    streamlit run main.py
    ```
4.  **Login**: Use the default credentials found in `credentials.txt` (default: `admin`, `admin123`).

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
    git commit -m "Added stock loan feature and audit log"
    ```

3.  **Push to Remote**:
    Upload your changes to GitHub (or your Git provider). Streamlit Cloud will automatically detect the new commit and redeploy the app.
    ```bash
    git push origin main
    ```
    *(Note: Replace `main` with your branch name if different, e.g., `master`)*

### Troubleshooting Deployment

*   If the app doesn't update immediately, check your Streamlit Cloud dashboard for build logs.
*   Ensure `requirements.txt` (if present) includes all necessary libraries (`streamlit`, `pandas`). Since this project uses standard libraries like `sqlite3`, `random`, `time`, `os`, `datetime`, usually only `streamlit` and `pandas` need explicit installation in the environment.
