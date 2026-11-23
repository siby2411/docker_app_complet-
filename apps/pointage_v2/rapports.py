"""Omega Pointage V2 — Rapports (à venir)"""
from flask import Blueprint
rapports_bp = Blueprint('rapports', __name__)
_deps = {}
def init_rapports(app, **kwargs):
    _deps.update(kwargs)
    app.register_blueprint(rapports_bp)
    print("[RAPPORTS] ✅ stub enregistré")
