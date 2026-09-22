import secrets
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import User
from app.routes.auth_forms import (
    RegisterForm, LoginForm, ForgotPasswordForm, ResetPasswordForm,
    ProfileForm, ChangePasswordForm,
)
from app.utils.email import send_password_reset_email, send_verification_email
from app.utils.audit import log_action

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data.strip(),
            email=form.email.data.lower().strip(),
            phone=form.phone.data.strip(),
            role="user",
            verification_token=secrets.token_urlsafe(32),
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        verify_url = url_for("auth.verify_email", token=user.verification_token, _external=True)
        send_verification_email(user, verify_url)
        log_action("user_registered", f"New account: {user.email}", user_id=user.id)

        flash("Account created! Check your email to verify your address, then sign in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/verify-email/<token>")
def verify_email(token):
    user = User.query.filter_by(verification_token=token).first()
    if user is None:
        flash("Invalid or expired verification link.", "danger")
        return redirect(url_for("auth.login"))
    user.email_verified = True
    user.verification_token = None
    db.session.commit()
    flash("Email verified successfully. You can now sign in.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()

        if user is None or not user.check_password(form.password.data):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html", form=form)

        if not user.is_active_account:
            flash("This account has been deactivated. Contact an administrator.", "warning")
            return render_template("auth/login.html", form=form)

        login_user(user, remember=form.remember_me.data)
        user.last_login = datetime.utcnow()
        db.session.commit()
        log_action("user_login", f"{user.email} signed in", user_id=user.id)

        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)
        return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    log_action("user_logout", f"{current_user.email} signed out", user_id=current_user.id)
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user:
            token = user.generate_reset_token()
            db.session.commit()
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            send_password_reset_email(user, reset_url)
        # Same message whether or not the account exists, to avoid leaking
        # which emails are registered.
        flash("If that email is registered, a reset link has been sent.", "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if user is None or not user.verify_reset_token(token):
        flash("That reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.forgot_password"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.clear_reset_token()
        db.session.commit()
        log_action("password_reset", f"{user.email} reset their password", user_id=user.id)
        flash("Password updated. You can now sign in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", form=form, token=token)


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    password_form = ChangePasswordForm()

    if form.submit.data and form.validate_on_submit():
        current_user.name = form.name.data.strip()
        current_user.phone = form.phone.data.strip()
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("auth.profile"))

    return render_template("auth/profile.html", form=form, password_form=password_form)


@auth_bp.route("/profile/change-password", methods=["POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "danger")
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            log_action("password_changed", f"{current_user.email} changed their password",
                       user_id=current_user.id)
            flash("Password changed successfully.", "success")
    return redirect(url_for("auth.profile"))
