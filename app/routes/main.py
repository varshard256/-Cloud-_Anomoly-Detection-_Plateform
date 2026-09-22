from flask import Blueprint, render_template
from flask_login import current_user

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    if current_user.is_authenticated:
        from flask import redirect, url_for
        return redirect(url_for("dashboard.index"))
    return render_template("main/home.html")


@main_bp.route("/about")
def about():
    return render_template("main/about.html")


@main_bp.route("/features")
def features():
    return render_template("main/features.html")


@main_bp.route("/pricing")
def pricing():
    return render_template("main/pricing.html")


@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    return render_template("main/contact.html")


@main_bp.route("/help")
def help_center():
    return render_template("main/help.html")
