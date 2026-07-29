from database.data_manager import db


class CompositionModel(db.Model):
    """
    Référentiel ANSM (CIS_COMPO_bdpm.txt) — substances actives d'une spécialité.
    Une spécialité peut avoir plusieurs lignes (associations de plusieurs SA).
    """
    __tablename__ = 'compositions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cis = db.Column(db.String(8), db.ForeignKey('specialites.cis'), nullable=False, index=True)

    code_substance = db.Column(db.String(20))
    denomination_substance = db.Column(db.String(255), nullable=False)
    dosage_substance = db.Column(db.String(100))
    reference_dosage = db.Column(db.String(255))
    nature_composant = db.Column(db.String(10))   # 'SA' = substance active, 'FT' = fraction thérapeutique
    numero_liaison = db.Column(db.String(10))

    # Normalisée pour matcher directement avec InteractionModel.ingredient_a/b
    search_substance = db.Column(db.String(255), index=True)

    specialite = db.relationship("SpecialiteModel", back_populates="compositions")

    def __repr__(self):
        return f"<Composition {self.cis} {self.denomination_substance} {self.dosage_substance}>"