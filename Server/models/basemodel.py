from database import data_manager as db
from sqlalchemy.exc import IntegrityError


class BaseModel(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.id}>"

    def save_to_db(self):
        try:
            db.session.add(self)
            db.session.commit()
            return True
        except IntegrityError as e:
            db.session.rollback()
            print(f"Error saving {self}: {e}")
            return False
        except Exception as e:
            db.session.rollback()
            print(f"Unexpected error saving {self}: {e}")
            return False

    def delete_from_db(self):
        try:
            db.session.delete(self)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error deleting {self}: {e}")
            return False
            db.session.delete(self)
            db.session.commit()
            return True    