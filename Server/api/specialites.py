from flask import request
from flask_restx import Resource, Namespace, fields
from flask_jwt_extended import jwt_required
from services.facade import FacadeService

specialites_ns = Namespace('specialites', description='ANSM referential search (read-only)')
facade = FacadeService()

specialite_model = specialites_ns.model('Specialite', {
    'cis': fields.String(description='Code CIS ANSM'),
    'denomination': fields.String(description='Nom officiel ANSM'),
    'forme_pharmaceutique': fields.String(description='Forme galénique'),
    'voies_administration': fields.String(description='Voie d\'administration'),
    'etat_commercialisation': fields.String(description='Statut de commercialisation'),
    'active_ingredients': fields.List(fields.String, description='Substances actives (SA)'),
})


@specialites_ns.route('/search')
class SpecialiteSearch(Resource):
    @jwt_required()
    @specialites_ns.doc(
        summary="Rechercher des spécialités ANSM",
        description="Recherche des spécialités par dénomination ou directement par code CIS.",
        params={'q': 'Terme de recherche (nom ou code CIS, min. 3 caractères)'}
    )
    @specialites_ns.marshal_list_with(specialite_model)
    def get(self):
        """Recherche des spécialités ANSM par nom ou CIS pour lier un produit du stock."""
        term = request.args.get('q', '').strip()
        if len(term) < 3:
            specialites_ns.abort(400, message="Le terme de recherche doit contenir au moins 3 caractères.")
        
        # Le FacadeService gère automatiquement si 'term' est un nom ou un code CIS
        results = facade.find_specialite_by_name(term, limit=10)
        return [r.to_dict() for r in results], 200


@specialites_ns.route('/<string:cis>')
@specialites_ns.param('cis', 'Code CIS à 8 chiffres de la spécialité')
class SpecialiteDetail(Resource):
    @jwt_required()
    @specialites_ns.doc(summary="Obtenir le détail d'une spécialité")
    @specialites_ns.marshal_with(specialite_model)
    def get(self, cis):
        """Détail d'une spécialité ANSM (composition incluse)."""
        specialite = facade.get_specialite_by_cis(cis)
        if not specialite:
            specialites_ns.abort(404, message="Spécialité ANSM introuvable.")
        return specialite.to_dict(), 200