# Ustawienia dla OpenAI API
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

# Włącz funkcję function calling - WAŻNE: ustaw na True
USE_FUNCTION_CALLING = True

# Ustawienia dla bazy danych 