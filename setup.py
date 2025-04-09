import os
import sys
import subprocess
import venv
from pathlib import Path
import secrets
import shutil

def check_python_version():
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)

def cleanup_venv():
    print("Cleaning up existing virtual environment...")
    venv_path = Path('venv')
    if venv_path.exists():
        try:
            shutil.rmtree(venv_path)
            print("Existing virtual environment removed.")
        except Exception as e:
            print(f"Warning: Could not remove existing virtual environment: {str(e)}")

def create_venv():
    print("Creating virtual environment...")
    venv.create('venv', with_pip=True)
    print("Virtual environment created successfully!")

def install_dependencies():
    print("Installing dependencies...")
    if sys.platform == "win32":
        pip_path = os.path.join('venv', 'Scripts', 'pip')
        python_path = os.path.join('venv', 'Scripts', 'python')
    else:
        pip_path = os.path.join('venv', 'bin', 'pip')
        python_path = os.path.join('venv', 'bin', 'python')
    
    # Upgrade pip first
    subprocess.run([python_path, '-m', 'pip', 'install', '--upgrade', 'pip'], check=True)
    
    # Install dependencies
    subprocess.run([pip_path, 'install', '-r', 'requirements.txt'], check=True)
    print("Dependencies installed successfully!")

def setup_env():
    print("Setting up environment variables...")
    env_path = Path('.env')
    
    if not env_path.exists():
        # Generate a secure secret key
        secret_key = secrets.token_hex(32)
        
        # Create .env file with default values
        with open('.env', 'w') as f:
            f.write(f'SECRET_KEY={secret_key}\n')
            f.write('OPENAI_API_KEY=your_openai_api_key_here\n')
        print("Created .env file with default values. Please update the OPENAI_API_KEY with your actual key.")
    else:
        print(".env file already exists. Skipping creation.")

def init_db():
    print("Initializing database...")
    if sys.platform == "win32":
        python_path = os.path.join('venv', 'Scripts', 'python')
    else:
        python_path = os.path.join('venv', 'bin', 'python')
    
    try:
        subprocess.run([python_path, 'init_db.py'], check=True)
        print("Database initialized successfully!")
    except subprocess.CalledProcessError as e:
        print("Warning: Database initialization failed. This might be due to OpenAI configuration.")
        print("You can initialize the database later after setting up your OpenAI API key.")
        print("Error details:", str(e))

def create_run_script():
    print("Creating run script...")
    if sys.platform == "win32":
        run_script_path = os.path.abspath('run.bat')
        with open(run_script_path, 'w') as f:
            f.write('@echo off\n')
            f.write('echo Activating virtual environment...\n')
            f.write('call .\\venv\\Scripts\\activate\n')
            f.write('echo Starting application...\n')
            f.write('python app.py\n')
            f.write('echo.\n')
            f.write('echo If the application closed unexpectedly, check the error message above.\n')
            f.write('pause\n')
        print(f"Created run.bat script at {run_script_path}")
    else:
        run_script_path = os.path.abspath('run.sh')
        with open(run_script_path, 'w') as f:
            f.write('#!/bin/bash\n')
            f.write('echo "Activating virtual environment..."\n')
            f.write('source venv/bin/activate\n')
            f.write('echo "Starting application..."\n')
            f.write('python app.py\n')
        # Make the script executable
        os.chmod(run_script_path, 0o755)
        print(f"Created run.sh script at {run_script_path}")

def main():
    try:
        # Check Python version
        check_python_version()
        
        # Cleanup existing virtual environment
        cleanup_venv()
        
        # Create virtual environment
        create_venv()
        
        # Install dependencies
        install_dependencies()
        
        # Setup environment variables
        setup_env()
        
        # Initialize database
        init_db()
        
        # Create run script
        create_run_script()
        
        print("\nSetup completed successfully!")
        print("\nTo run the application:")
        if sys.platform == "win32":
            print("1. Double-click run.bat or run from command line:")
            print("   run.bat")
        else:
            print("1. Run from command line:")
            print("   ./run.sh")
        
        print("\nAlternatively, you can run manually:")
        if sys.platform == "win32":
            print("1. Activate virtual environment: .\\venv\\Scripts\\activate")
        else:
            print("1. Activate virtual environment: source venv/bin/activate")
        print("2. Run the application: python app.py")
        
        print("\nNote: If you haven't set up your OpenAI API key yet:")
        print("1. Open the .env file")
        print("2. Replace 'your_openai_api_key_here' with your actual OpenAI API key")
        print("3. Run the application again")
        
    except Exception as e:
        print(f"Error during setup: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 