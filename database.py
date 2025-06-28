import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, Float, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

# Path file database SQLite. Pastikan folder 'data' ada.
DATABASE_URL = "sqlite:///./data/my_data.db"

# Base untuk model deklaratif SQLAlchemy
Base = declarative_base()

# Definisikan model data Anda (tabel 'actual_data')
class ActualData(Base):
    __tablename__ = "actual_data"
    
    # Kolom 'id':
    # - Integer: Tipe data integer
    # - primary_key=True: Ini adalah kunci utama tabel, memastikan setiap baris unik.
    # - index=True: Membuat indeks pada kolom ini untuk pencarian yang sangat cepat berdasarkan ID.
    #   SQLAlchemy dan SQLite akan otomatis membuatnya auto-incrementing.
    id = Column(Integer, primary_key=True, index=True)
    
    # Kolom 'date':
    # - Date: Tipe data tanggal
    # - unique=True: Memastikan tidak ada dua entri dengan tanggal yang sama.
    # - index=True: Membuat indeks pada kolom ini untuk pencarian dan pengurutan berdasarkan tanggal yang efisien.
    date = Column(Date, unique=True, index=True) 
    
    # Kolom 'value':
    # - Float: Tipe data angka desimal (misalnya harga saham, penjualan).
    value = Column(Float)

    # Representasi string objek saat dicetak (opsional, untuk debugging)
    def __repr__(self):
        return f"<ActualData(id={self.id}, date={self.date}, value={self.value})>"

# Buat engine database
engine = create_engine(DATABASE_URL)

# Buat tabel jika belum ada di database
Base.metadata.create_all(engine)

# Buat session factory untuk berinteraksi dengan database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Fungsi generator untuk mendapatkan sesi database dan menutupnya setelah digunakan
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Fungsi CRUD Dasar ---
def create_data(db_session, date: datetime.date, value: float):
    db_data = ActualData(date=date, value=value)
    db_session.add(db_data)
    db_session.commit()
    db_session.refresh(db_data)
    return db_data

def get_all_data(db_session):
    return db_session.query(ActualData).order_by(ActualData.date).all()

def get_data_by_id(db_session, data_id: int):
    return db_session.query(ActualData).filter(ActualData.id == data_id).first()

def update_data(db_session, data_id: int, new_date: datetime.date, new_value: float):
    db_data = db_session.query(ActualData).filter(ActualData.id == data_id).first()
    if db_data:
        db_data.date = new_date
        db_data.value = new_value
        db_session.commit()
        db_session.refresh(db_data)
        return db_data
    return None

def delete_data(db_session, data_id: int):
    db_data = db_session.query(ActualData).filter(ActualData.id == data_id).first()
    if db_data:
        db_session.delete(db_data)
        db_session.commit()
        return True
    return False