from database.data_manager import db


class InteractionAnsmModel(db.Model):
    """
    Référentiel complet des interactions médicamenteuses issu du Thésaurus
    ANSM (PDF -> CSV via utils/parse_ansm_thesaurus.py).

    Complète InteractionModel (~30 lignes manuellement curées) sans le
    remplacer : InteractionModel reste la source prioritaire/vérifiée,
    cette table sert de filet de sécurité plus large (3200+ paires).
    """
    __tablename__ = 'interactions_ansm'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    substance_a = db.Column(db.String(255), nullable=False)
    substance_b = db.Column(db.String(255), nullable=False)
    substance_a_norm = db.Column(db.String(255), index=True)
    substance_b_norm = db.Column(db.String(255), index=True)
    _severity = db.Column("severity", db.String(20))  # critical / high / moderate / low
    ansm_codes = db.Column(db.String(30))       # ex: "CI;PE"
    mechanism = db.Column(db.Text)
    conduct = db.Column(db.Text)
    source_page = db.Column(db.Integer)

    @property
    def severity(self) -> str:
        """
        Harmonise la sévérité avec la majuscule initiale de InteractionModel
        (ex: 'high' -> 'High', 'critical' -> 'Critical').
        """
        if not self._severity:
            return "High"
        return self._severity.strip().capitalize()

    @severity.setter
    def severity(self, value: str):
        """Permet de définir la sévérité en nettoyant la valeur."""
        self._severity = value.strip().lower() if value else None

    @property
    def description(self) -> str:
        """
        Expose la même interface que InteractionModel.description, pour que
        ChatBot_engine._handle_interaction_check() n'ait RIEN à changer
        (il lit juste ix.severity et ix.description, peu importe la source).
        """
        parts = [self.mechanism or ""]
        if self.conduct:
            parts.append(f"Conduite à tenir : {self.conduct}")
        return " ".join(p for p in parts if p).strip()

    def __repr__(self):
        return f"<InteractionAnsm {self.substance_a} + {self.substance_b} ({self.severity})>"