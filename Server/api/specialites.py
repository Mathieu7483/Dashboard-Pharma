from flask import request
from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required
from services.facade import FacadeService

specialites_ns = Namespace('specialites', description='ANSM referential search (read-only)')
facade = FacadeService()

specialite_model = specialites_ns.model('Specialite', {
    'cis': fields.String(description='Code CIS ANSM'),
    'denomination': fields.String(description='Nom officiel ANSM'),
    'forme_pharmaceutique': fields.String,
    'voies_administration': fields.String,
    'etat_commercialisation': fields.String,
    'active_ingredients': fields.List(fields.String, description='Substances actives (SA)'),
})


@specialites_ns.route('/search')
class SpecialiteSearch(Resource):
    @jwt_required()
    @specialites_ns.doc(params={'q': 'Terme de recherche (nom du médicament)'})
    @specialites_ns.marshal_list_with(specialite_model)
    def get(self):
        """Recherche des spécialités ANSM par nom, pour lier un produit du stock."""
        term = request.args.get('q', '').strip()
        if len(term) < 3:
            specialites_ns.abort(400, message="Le terme de recherche doit contenir au moins 3 caractères.")
        results = facade.find_specialite_by_name(term, limit=10)
        return [r.to_dict() for r in results], 200


@specialites_ns.route('/<string:cis>')
@specialites_ns.param('cis', 'Code CIS de la spécialité')
class SpecialiteDetail(Resource):
    @jwt_required()
    @specialites_ns.marshal_with(specialite_model)
    def get(self, cis):
        """Détail d'une spécialité ANSM (composition incluse)."""
        specialite = facade.get_specialite_by_cis(cis)
        if not specialite:
            specialites_ns.abort(404, message="Spécialité ANSM introuvable.")
        return specialite.to_dict(), 200