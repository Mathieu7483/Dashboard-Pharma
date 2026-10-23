from database.data_manager import db


class SpecialiteModel(db.Model):
    """
    Référentiel ANSM (CIS_bdpm.txt) — une spécialité pharmaceutique.
    Table pilotée uniquement par utils/import_ansm.py, ne pas éditer à la main.
    """
    __tablename__ = 'specialites'

    cis = db.Column(db.String(8), primary_key=True)
    denomination = db.Column(db.String(500), nullable=False, index=True)
    forme_pharmaceutique = db.Column(db.String(255))
    voies_administration = db.Column(db.String(255))
    statut_amm = db.Column(db.String(100))
    type_procedure = db.Column(db.String(150))
    etat_commercialisation = db.Column(db.String(150))

    # Nom normalisé (sans accents, minuscule) pour la recherche/le matching du chatbot
    search_name = db.Column(db.String(500), index=True)

    compositions = db.relationship(
        "CompositionModel", back_populates="specialite",
        cascade="all, delete-orphan", lazy=True
    )

    def to_dict(self):
        return {
            'cis': self.cis,
            'denomination': self.denomination,
            'forme_pharmaceutique': self.forme_pharmaceutique,
            'voies_administration': self.voies_administration,
            'etat_commercialisation': self.etat_commercialisation,
            'active_ingredients': [
                c.denomination_substance for c in self.compositions
                if c.nature_composant == 'SA'
            ],
        }

    def __repr__(self):
        return f"<Specialite {self.cis} {self.denomination}>"