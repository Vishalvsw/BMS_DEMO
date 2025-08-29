from functools import wraps
from flask import session, redirect, url_for, flash, make_response

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If session expired / not logged in → redirect
        if "admin_id" not in session:
            flash("Please login to access this page.", "warning")
            return redirect(url_for("login"))

        # Otherwise process request normally
        response = make_response(f(*args, **kwargs))

        # 🔒 Force browser to always reload from server
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return decorated_function
