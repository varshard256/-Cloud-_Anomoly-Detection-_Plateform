from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required

from app.extensions import db
from app.models import User, SystemLog
from app.utils.decorators import admin_required
from app.utils.audit import log_action

admin_bp = Blueprint("admin", __name__, url_prefix="/admin", template_folder="../templates/admin")


@admin_bp.route("/users")
@login_required
@admin_required
def users():
    page = request.args.get("page", 1, type=int)
    pagination = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=15)
    return render_template("admin/users.html", pagination=pagination, users=pagination.items)


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@login_required
@admin_required
def toggle_user_active(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active_account = not user.is_active_account
    db.session.commit()
    log_action("admin_toggle_user", f"{'Activated' if user.is_active_account else 'Deactivated'} {user.email}")
    flash(f"{user.name}'s account has been {'activated' if user.is_active_account else 'deactivated'}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/make-admin", methods=["POST"])
@login_required
@admin_required
def make_admin(user_id):
    user = User.query.get_or_404(user_id)
    user.role = "admin"
    db.session.commit()
    log_action("admin_role_grant", f"{user.email} promoted to admin")
    flash(f"{user.name} is now an administrator.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/logs")
@login_required
@admin_required
def logs():
    page = request.args.get("page", 1, type=int)
    pagination = SystemLog.query.order_by(SystemLog.created_at.desc()).paginate(page=page, per_page=25)
    return render_template("admin/logs.html", pagination=pagination, logs=pagination.items)
