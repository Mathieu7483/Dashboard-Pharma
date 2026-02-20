from database.data_manager import db

class InteractionModel(db.Model):
    __tablename__ = 'interactions'

    id = db.Column(db.Integer, primary_key=True)
    ingredient_a = db.Column(db.String(100), nullable=False)
    ingredient_b = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), nullable=False) # Critical, High, Moderate
    description = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<Interaction {self.ingredient_a} / {self.ingredient_b}>"