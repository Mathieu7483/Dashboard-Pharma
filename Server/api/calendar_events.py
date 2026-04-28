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
    'type':         fields.String(required=True, enum=['rdv', 'garde']),
    'title':        fields.String(description='Title or contact name'),
    'startDate':    fields.String(required=True, description='YYYY-MM-DD'),
    'endDate':      fields.String(description='YYYY-MM-DD'),
    'startTime':    fields.String(required=True, description='HH:MM'),
    'endTime':      fields.String(required=True, description='HH:MM'),
    'notes':        fields.String(),
    'assignedUser': fields.String(description='ID of the assigned user')
})

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
            events = db.session.execute(
                db.select(CalendarEvent).order_by(
                    CalendarEvent.start_date.asc(),
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

        assigned = data.get('assignedUser')
        print(f"📥 POST /calendar/events/ — type={data.get('type')!r} assignedUser={assigned!r}")

        try:
            new_event = CalendarEvent(
                type=data['type'],
                title=data.get('title') or 'Sans titre',
                start_date=data['startDate'],
                end_date=data.get('endDate') or data['startDate'],
                start_time=data['startTime'],
                end_time=data['endTime'],
                notes=data.get('notes'),
                assigned_user_id=assigned if assigned else None,
                created_by=current_user_id
            )
            db.session.add(new_event)
            db.session.commit()
            print(f"   ✅ assigned_user_id en DB = {new_event.assigned_user_id!r}")
            return new_event.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            print(f"   ❌ {e}")
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
    @calendar_ns.expect(update_events_model)
    def put(self, user_id):
        """Mass update events for a user (Admin Access)"""
        data = request.get_json()
        event_ids = data.get('eventIds', [])
        try:
            db.session.query(CalendarEvent).filter_by(assigned_user_id=user_id).update({'assigned_user_id': None})
            if event_ids:
                db.session.query(CalendarEvent).filter(
                    CalendarEvent.id.in_(event_ids)
                ).update({'assigned_user_id': user_id}, synchronize_session=False)
            db.session.commit()
            return {'message': 'Update successful'}, 200
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 500


# ─── FIX: PUT ajouté — manquait complètement dans la version originale ───
@calendar_ns.route('/events/<string:event_id>')
class EventDetail(Resource):

    @jwt_required()
    @admin_required()
    def get(self, event_id):
        """Get a single event by ID (Admin Access)"""
        event = db.session.get(CalendarEvent, event_id)
        if not event:
            return {'message': 'Event not found'}, 404
        return event.to_dict(), 200

    @jwt_required()
    @admin_required()
    @calendar_ns.expect(event_model)
    def put(self, event_id):
        """Update an existing event (Admin Access)"""
        event = db.session.get(CalendarEvent, event_id)
        if not event:
            return {'message': 'Event not found'}, 404

        data = request.get_json()
        assigned = data.get('assignedUser')
        print(f"📥 PUT /calendar/events/{event_id} — assignedUser={assigned!r}")

        try:
            if 'type'         in data: event.type       = data['type']
            if 'title'        in data: event.title      = data.get('title') or 'Sans titre'
            if 'startDate'    in data: event.start_date = data['startDate']
            if 'endDate'      in data: event.end_date   = data.get('endDate') or event.start_date
            if 'startTime'    in data: event.start_time = data['startTime']
            if 'endTime'      in data: event.end_time   = data['endTime']
            if 'notes'        in data: event.notes      = data.get('notes')
            if 'assignedUser' in data: event.assigned_user_id = assigned if assigned else None

            db.session.commit()
            print(f"   ✅ assigned_user_id = {event.assigned_user_id!r}")
            return event.to_dict(), 200
        except Exception as e:
            db.session.rollback()
            print(f"   ❌ {e}")
            return {'message': str(e)}, 500

    @jwt_required()
    @admin_required()
    def delete(self, event_id):
        """Delete an event (Admin Access)"""
        event = db.session.get(CalendarEvent, event_id)
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
        today = datetime.now().strftime('%Y-%m-%d')
        try:
            rdv_count   = db.session.query(CalendarEvent).filter_by(type='rdv',   start_date=today).count()
            garde_count = db.session.query(CalendarEvent).filter_by(type='garde', start_date=today).count()
            total       = rdv_count + garde_count
            return {
                'today':       today,
                'rdv_count':   rdv_count,
                'garde_count': garde_count,
                'total':       total,
                'total_all':   total   # FIX: JS cherche 'total_all'
            }, 200
        except Exception as e:
            return {'message': str(e)}, 500