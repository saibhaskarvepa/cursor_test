import os
import sys
import subprocess
import venv
from pathlib import Path
import secrets

def create_venv():
    print("Creating virtual environment...")
    venv.create('venv', with_pip=True)
    print("Virtual environment created successfully!")

def install_dependencies():
    print("Installing dependencies...")
    if sys.platform == "win32":
        pip_path = os.path.join('venv', 'Scripts', 'pip')
    else:
        pip_path = os.path.join('venv', 'bin', 'pip')
    
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
    
    subprocess.run([python_path, 'init_db.py'], check=True)
    print("Database initialized successfully!")

def main():
    try:
        # Create virtual environment
        create_venv()
        
        # Install dependencies
        install_dependencies()
        
        # Setup environment variables
        setup_env()
        
        # Initialize database
        init_db()
        
        print("\nSetup completed successfully!")
        print("\nTo run the application:")
        if sys.platform == "win32":
            print("1. Activate virtual environment: .\\venv\\Scripts\\activate")
        else:
            print("1. Activate virtual environment: source venv/bin/activate")
        print("2. Run the application: python app.py")
        
    except Exception as e:
        print(f"Error during setup: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 