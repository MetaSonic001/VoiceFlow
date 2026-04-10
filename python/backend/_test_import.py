try:
    from main import app
    print("OK - app loaded")
    routes = [r.path for r in app.routes]
    tts_routes = [r for r in routes if "tts" in r]
    print(f"Total routes: {len(routes)}")
    print(f"TTS routes: {tts_routes}")
except Exception as e:
    import traceback
    traceback.print_exc()
