"""Omega Pointage V2 — Portail (à venir)"""
from flask import Blueprint, redirect
portail_bp = Blueprint('portail', __name__)
_deps = {}
def init_portail(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(portail_bp)
    print("[PORTAIL] ✅ stub enregistré")

@portail_bp.route('/portail')
def portail_index():
    return redirect('/login')
