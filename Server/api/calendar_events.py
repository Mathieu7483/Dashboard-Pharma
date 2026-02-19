# routes/calendar_events.py

from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.calendar import CalendarEvent
from database.data_manager import db 
from utils.decorator import admin_required 
from datetime import datetime

calendar_ns = Namespace('calendar', description="Calendar Management - Admin Only")

# ─────────────────────────────────────────────
# SWAGGER MODELS
# ─────────────────────────────────────────────
event_model = calendar_ns.model('CalendarEvent', {
    'type': fields.String(required=True, enum=['rdv', 'garde']),
    'title': fields.String(description='Title or contact name'),
    'startDate': fields.String(required=True, description='YYYY-MM-DD'),
    'endDate': fields.String(description='YYYY-MM-DD'),
    'startTime': fields.String(required=True, description='HH:MM'),
    'endTime': fields.String(required=True, description='HH:MM'),
    'notes': fields.String(),
    'assignedUser': fields.String(description='ID of the assigned user')
})

# Update model for mass updates
update_events_model = calendar_ns.model('UpdateUserEvents', {
    'eventIds': fields.List(fields.String, required=True, description='List of Event IDs to assign')
})

# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@calendar_ns.route('/events/')
class EventList(Resource):

    @jwt_required()
    @admin_required() 
    def get(self):
        """List all events (Admin Access)"""
        try:
            # Querying using the session for consistency with ChatBotEngine
            events = db.session.execute(
                db.select(CalendarEvent).order_by(
                    CalendarEvent.start_date.desc(), 
                    CalendarEvent.start_time.asc()
                )
            ).scalars().all()
            return [e.to_dict() for e in events], 200
        except Exception as e:
            return {'message': f'Server error: {str(e)}'}, 500

    @jwt_required()
    @admin_required()
    @calendar_ns.expect(event_model)
    def post(self):
        """Create a Meeting or Shift (Admin Access)"""
        data = request.get_json()
        current_user_id = get_jwt_identity()

        try:
            new_event = CalendarEvent(
                type=data['type'],
                title=data.get('title', 'Sans titre'),
                start_date=data['startDate'],
                # Logic: If endDate is missing, default to startDate
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

@calendar_ns.route('/events/user/<string:user_id>')
class UserEvents(Resource):
    
    @jwt_required()
    @admin_required()
    def get(self, user_id):
        """Get events assigned to a specific user (Admin Access)"""
        try:
            events = db.session.execute(
                db.select(CalendarEvent)
                .where(CalendarEvent.assigned_user_id == user_id)
                .order_by(CalendarEvent.start_date.desc())
            ).scalars().all()
            return [e.to_dict() for e in events], 200
        except Exception as e:
            return {'message': str(e)}, 500
        
    @jwt_required()
    @admin_required()
    @calendar_ns.expect(update_events_model) # Added missing documentation
    def put(self, user_id):
        """Mass update events for a user (Admin Access)"""
        data = request.get_json()
        event_ids = data.get('eventIds', [])
        
        try:
            # Step 1: Unassign previous events for this user
            db.session.query(CalendarEvent).filter_by(assigned_user_id=user_id).update({'assigned_user_id': None})
            
            # Step 2: Assign new events from the provided list
            if event_ids:
                db.session.query(CalendarEvent).filter(CalendarEvent.id.in_(event_ids)).update(
                    {'assigned_user_id': user_id}, 
                    synchronize_session=False
                )
            
            db.session.commit()
            return {'message': 'Update successful'}, 200
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 500

@calendar_ns.route('/events/<string:event_id>')
class EventDetail(Resource):

    @jwt_required()
    @admin_required()
    def delete(self, event_id):
        """Delete an event (Admin Access)"""
        event = db.session.get(CalendarEvent, event_id) # Modern SQLAlchemy 2.0 style
        if not event:
            return {'message': 'Event not found'}, 404
        
        try:
            db.session.delete(event)
            db.session.commit()
            return {'message': 'Deleted successfully'}, 200
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 500

@calendar_ns.route('/events/stats/today')
class EventTodayStats(Resource):

    @jwt_required()
    @admin_required()
    def get(self):
        """Quick stats for today (Admin Access)"""
        today = datetime.now().strftime('%Y-%m-%d') # Use now() instead of utcnow() (deprecated in Python 3.12+)
        try:
            rdv_count = db.session.query(CalendarEvent).filter(
                CalendarEvent.type == 'rdv', 
                CalendarEvent.start_date == today
            ).count()
            
            garde_count = db.session.query(CalendarEvent).filter(
                CalendarEvent.type == 'garde', 
                CalendarEvent.start_date == today
            ).count()
            
            return {
                'today': today,
                'rdv_count': rdv_count,
                'garde_count': garde_count,
                'total': rdv_count + garde_count
            }, 200
        except Exception as e:
            return {'message': str(e)}, 500