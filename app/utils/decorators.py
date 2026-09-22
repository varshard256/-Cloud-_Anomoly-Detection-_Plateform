from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user


def admin_required(f):
    """Restrict a view to authenticated admins only."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_admin:
            flash("You don't have permission to access that page.", "danger")
            return abort(403)
        return f(*args, **kwargs)

    return decorated


def active_account_required(f):
    """Block deactivated accounts from reaching protected views."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.is_authenticated and not current_user.is_active_account:
            flash("Your account has been deactivated. Contact an administrator.", "warning")
            return redirect(url_for("auth.logout"))
        return f(*args, **kwargs)

    return decorated
