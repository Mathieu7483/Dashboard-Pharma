from database.data_manager import db


class ClasseMembreModel(db.Model):
    """Appartenance substance -> classe ANSM (générée depuis le thésaurus)."""
    __tablename__ = "classes_ansm"

    id = db.Column(db.Integer, primary_key=True)
    classe_norm = db.Column(db.String(200), nullable=False, index=True)
    membre_norm = db.Column(db.String(200), nullable=False, index=True)

    __table_args__ = (db.UniqueConstraint("classe_norm", "membre_norm", name="uq_classe_membre"),)
