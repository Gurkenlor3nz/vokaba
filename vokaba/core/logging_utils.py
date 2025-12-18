from datetime import datetime

def log(text: str) -> None:
    print(f'LOG  time: {str(datetime.now())[11:]} ; content: "{text}"')
