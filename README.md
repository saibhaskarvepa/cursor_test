# Video Processing Application

A Flask-based application for processing YouTube videos with features like translation, transcription, and more.

## Prerequisites

- Python 3.8 or higher
- Git

## Quick Start

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd <repo-name>
   ```

2. Run the setup script:
   ```bash
   python setup.py
   ```
   This will:
   - Create a virtual environment
   - Install all dependencies
   - Set up environment variables
   - Initialize the database
   - Create a run script

3. Run the application:
   - On Windows:
     - Double-click `run.bat` or run from command line:
       ```bash
       run.bat
       ```
   - On macOS/Linux:
     - Run from command line:
       ```bash
       ./run.sh
       ```

The application will be available at `http://localhost:5000`

## Manual Setup (Alternative)

If you prefer to run manually:

1. Activate the virtual environment:
   - On Windows:
     ```bash
     .\venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

2. Run the application:
   ```bash
   python app.py
   ```

## Environment Variables

The setup script automatically creates a `.env` file with the following variables:
- `SECRET_KEY`: Automatically generated secure key for JWT tokens
- `OPENAI_API_KEY`: You need to update this with your actual OpenAI API key

## Features

- User authentication and authorization
- YouTube video processing
- Translation and transcription services
- Admin dashboard
- Real-time progress updates

## Project Structure

- `app.py`: Main application file
- `openai_service.py`: OpenAI service integration
- `download.py`: YouTube video download functionality
- `init_db.py`: Database initialization
- `requirements.txt`: Python dependencies
- `setup.py`: Automated setup script
- `run.bat`/`run.sh`: Convenience scripts to run the application

## Troubleshooting

If you encounter any issues:

1. Make sure Python 3.8 or higher is installed
2. Check if all dependencies are installed correctly
3. Verify that the `.env` file exists and contains the necessary variables
4. Ensure you have an active internet connection for YouTube downloads and OpenAI services
5. If you get "ModuleNotFoundError", make sure you've run the setup script and are using the run script or have activated the virtual environment

## Support

For any issues or questions, please contact the development team. 