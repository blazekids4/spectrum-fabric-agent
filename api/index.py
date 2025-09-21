from app import app as _app

# Export an ASGI callable that strips the '/api' prefix from the incoming HTTP path.
# Vercel will call this file for requests under /api/*; the request.path will include /api,
# but your FastAPI routes are defined for paths like '/chat' or '/api/...' in backend.app.
# We'll remove a single leading '/api' so routes line up. This avoids changing backend routes.
async def __vercel_app__(scope, receive, send):
    # Only adjust HTTP requests
    if scope.get("type") == "http":
        path = scope.get("path", "")
        if path.startswith("/api"):
            # copy scope to avoid mutating the original dict stored elsewhere
            scope = dict(scope)
            # strip the first '/api' segment
            scope["path"] = path[len("/api"):] or "/"
            # preserve root_path if you wish:
            # scope["root_path"] = "/api"
    await _app(scope, receive, send)

# Vercel looks for a top-level callable named 'app' or 'handler'. Expose both to be safe.
app = __vercel_app__
handler = __vercel_app__