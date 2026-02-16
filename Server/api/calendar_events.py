# routes/calendar_events.py

from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.calendar import CalendarEvent
from database.data_manager import db 
from utils.decorator import admin_required  # Import de ton décorateur
from datetime import datetime

calendar_ns = Namespace('calendar', description="Gestion du calendrier - Admin Only")

# ─────────────────────────────────────────────
# MODÈLES SWAGGER
# ─────────────────────────────────────────────
event_model = calendar_ns.model('CalendarEvent', {
    'type': fields.String(required=True, enum=['rdv', 'garde']),
    'title': fields.String(description='Titre ou nom du contact'),
    'startDate': fields.String(required=True, description='YYYY-MM-DD'),
    'endDate': fields.String(description='YYYY-MM-DD'),
    'startTime': fields.String(required=True, description='HH:MM'),
    'endTime': fields.String(required=True, description='HH:MM'),
    'notes': fields.String(),
    'assignedUser': fields.String(description='ID de l\'utilisateur assigné')
})

# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@calendar_ns.route('/events/')
class EventList(Resource):

    @jwt_required()
    @admin_required() # Utilisation de ton décorateur
    def get(self):
        """Liste tous les événements (Accès Admin)"""
        try:
            events = CalendarEvent.query.order_by(
                CalendarEvent.start_date.desc(), 
                CalendarEvent.start_time.asc()
            ).all()
            return [e.to_dict() for e in events], 200
        except Exception as e:
            return {'message': f'Server error: {str(e)}'}, 500

    @jwt_required()
    @admin_required()
    @calendar_ns.expect(event_model)
    def post(self):
        """Créer un RDV ou une Garde (Accès Admin)"""
        data = request.get_json()
        current_user_id = get_jwt_identity()

        try:
            new_event = CalendarEvent(
                type=data['type'],
                title=data.get('title', 'Sans titre'),
                start_date=data['startDate'],
                end_date=data.get('endDate') or data['startDate'],
                start_time=data['startTime'],
                end_time=data['endTime'],
                notes=data.get('notes'),
                assigned_user_id=data.get('assignedUser'),
                created_by=current_user_id
            )
            db.session.add(new_event)
            db.session.commit()
            return new_event.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 500

@calendar_ns.route('/events/<string:event_id>')
class EventDetail(Resource):

    @jwt_required()
    @admin_required()
    def delete(self, event_id):
        """Supprimer un événement (Accès Admin)"""
        event = CalendarEvent.query.get(event_id)
        if not event:
            return {'message': 'Événement introuvable'}, 404
        
        try:
            db.session.delete(event)
            db.session.commit()
            return {'message': 'Supprimé avec succès'}, 200
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 500

@calendar_ns.route('/events/stats/today')
class EventTodayStats(Resource):

    @jwt_required()
    @admin_required()
    def get(self):
        """Stats rapides (Accès Admin)"""
        today = datetime.utcnow().strftime('%Y-%m-%d')
        try:
            rdv_count = CalendarEvent.query.filter(CalendarEvent.type == 'rdv', CalendarEvent.start_date == today).count()
            garde_count = CalendarEvent.query.filter(CalendarEvent.type == 'garde', CalendarEvent.start_date == today).count()
            
            return {
                'today': today,
                'rdv_count': rdv_count,
                'garde_count': garde_count,
                'total': rdv_count + garde_count
            }, 200
        except Exception as e:
            return {'message': str(e)}, 500