from main import db
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class User(db.Model):
    """Example User model for the database."""
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    
    def __repr__(self):
        return f'<User {self.name}>'