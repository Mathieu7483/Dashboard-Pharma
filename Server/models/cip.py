from database.data_manager import db
from models.basemodel import BaseModel

class CipModel(BaseModel):
    """
    Modèle représentant les présentations / codes CIP associés à une spécialité ANSM (CIS_CIP.txt).
    """
    __tablename__ = 'cip_presentations'

    cis = db.Column(db.String(8), db.ForeignKey('specialites.cis'), nullable=False, index=True)
    cip7 = db.Column(db.String(7), nullable=True)
    libelle_presentation = db.Column(db.String(255), nullable=True)
    statut_admin = db.Column(db.String(100), nullable=True)
    etat_commercialisation = db.Column(db.String(50), nullable=True)
    cip13 = db.Column(db.String(13), nullable=False, index=True)

    def __init__(self, cis, cip7, libelle_presentation, statut_admin, etat_commercialisation, cip13):
        self.cis = cis
        self.cip7 = cip7
        self.libelle_presentation = libelle_presentation
        self.statut_admin = statut_admin
        self.etat_commercialisation = etat_commercialisation
        self.cip13 = cip13

    def to_dict(self):
        return {
            'id': str(self.id),
            'cis': self.cis,
            'cip7': self.cip7,
            'libelle_presentation': self.libelle_presentation,
            'cip13': self.cip13
        }