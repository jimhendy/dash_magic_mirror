import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# TFL Configuration
class TFLConfig:
    # Left side TFL stops
    LEFT_STOPS = []
    if os.getenv("TFL_LEFT_STOP_1_ID"):
        LEFT_STOPS.append({
            "id": os.getenv("TFL_LEFT_STOP_1_ID"),
            "name": os.getenv("TFL_LEFT_STOP_1_NAME", "Unknown Stop")
        })
    if os.getenv("TFL_LEFT_STOP_2_ID"):
        LEFT_STOPS.append({
            "id": os.getenv("TFL_LEFT_STOP_2_ID"), 
            "name": os.getenv("TFL_LEFT_STOP_2_NAME", "Unknown Stop")
        })
    
    # Right side TFL stops
    RIGHT_STOPS = []
    if os.getenv("TFL_RIGHT_STOP_1_ID"):
        RIGHT_STOPS.append({
            "id": os.getenv("TFL_RIGHT_STOP_1_ID"),
            "name": os.getenv("TFL_RIGHT_STOP_1_NAME", "Unknown Stop")
        })
    if os.getenv("TFL_RIGHT_STOP_2_ID"):
        RIGHT_STOPS.append({
            "id": os.getenv("TFL_RIGHT_STOP_2_ID"),
            "name": os.getenv("TFL_RIGHT_STOP_2_NAME", "Unknown Stop")
        })

# Component positioning
class PositionConfig:
    # Clock
    CLOCK_TOP = float(os.getenv("CLOCK_TOP", "0.0"))
    CLOCK_WIDTH = float(os.getenv("CLOCK_WIDTH", "0.4"))
    CLOCK_HEIGHT = float(os.getenv("CLOCK_HEIGHT", "0.2"))
    
    # TFL Left
    TFL_LEFT_LEFT = float(os.getenv("TFL_LEFT_LEFT", "0.05"))
    TFL_LEFT_TOP = float(os.getenv("TFL_LEFT_TOP", "0.7"))
    TFL_LEFT_WIDTH = float(os.getenv("TFL_LEFT_WIDTH", "0.25"))
    TFL_LEFT_HEIGHT = float(os.getenv("TFL_LEFT_HEIGHT", "0.3"))
    
    # TFL Right  
    TFL_RIGHT_RIGHT = float(os.getenv("TFL_RIGHT_RIGHT", "0.95"))
    TFL_RIGHT_TOP = float(os.getenv("TFL_RIGHT_TOP", "0.7"))
    TFL_RIGHT_WIDTH = float(os.getenv("TFL_RIGHT_WIDTH", "0.25"))
    TFL_RIGHT_HEIGHT = float(os.getenv("TFL_RIGHT_HEIGHT", "0.3"))
    
    # Compliments
    COMPLIMENTS_WIDTH = float(os.getenv("COMPLIMENTS_WIDTH", "0.5"))
    COMPLIMENTS_HEIGHT = float(os.getenv("COMPLIMENTS_HEIGHT", "0.25"))