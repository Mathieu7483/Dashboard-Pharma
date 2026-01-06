from services.facade import FacadeService # Importe ta façade
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required
from datetime import datetime

facade = FacadeService()

analytics_ns = Namespace('analytics', description='Analytics related operations')

@analytics_ns.route('/daily')
class DailySales(Resource):
    @jwt_required()
    def get(self):
        results = facade.get_daily_stats()
        graph_data = [
            {
                "hour": f"{int(r.hour)}h", 
                "revenue": float(r.revenue) if r.revenue else 0.0, 
                "sale_count": r.sale_count
            } for r in results
        ]
        return {"date": datetime.utcnow().strftime('%Y-%m-%d'), "graph_data": graph_data}, 200