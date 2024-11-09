import requests
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, Enum
from sqlalchemy.orm import sessionmaker, relationship, declarative_base

# Koneksi ke database MySQL
DATABASE_URL = (
    "mysql+pymysql://root:root@127.0.0.1:8889/alquran_db"
    "?unix_socket=/Applications/MAMP/tmp/mysql/mysql.sock"
)
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()

# Definisi tabel Surah
class Surah(Base):
    __tablename__ = 'surah'
    id = Column(Integer, primary_key=True)
    name_arabic = Column(String(255), nullable=False)
    name_english = Column(String(255), nullable=False)
    number_of_ayah = Column(Integer, nullable=False)
    revelation_place = Column(Enum('Mekah', 'Madinah'), nullable=False)
    revelation_order = Column(Integer, nullable=False)
    ayahs = relationship('Ayah', back_populates='surah')

# Definisi tabel Ayah
class Ayah(Base):
    __tablename__ = 'ayah'
    id = Column(Integer, primary_key=True)
    surah_id = Column(Integer, ForeignKey('surah.id'))
    ayah_number = Column(Integer, nullable=False)
    text_arabic = Column(Text, nullable=False)
    text_translation = Column(Text)
    juz_number = Column(Integer, ForeignKey('juz.number'))
    surah = relationship('Surah', back_populates='ayahs')
    juz = relationship('Juz', back_populates='ayahs')

# Definisi tabel Juz
class Juz(Base):
    __tablename__ = 'juz'
    number = Column(Integer, primary_key=True)
    start_surah = Column(Integer, ForeignKey('surah.id'))
    start_ayah = Column(Integer)
    end_surah = Column(Integer, ForeignKey('surah.id'))
    end_ayah = Column(Integer)
    ayahs = relationship('Ayah', back_populates='juz')

# Buat tabel di database
Base.metadata.create_all(engine)

# URL sumber data Al-Qur'an
quran_api_url = "https://equran.id/api/v2/surat"

# Pemetaan nilai tempat turun untuk mencocokkan dengan ENUM di database
revelation_mapping = {
    'Meccan': 'Mekah',
    'Medinan': 'Madinah'
}

# Ambil data surah dari API
response = requests.get(quran_api_url)
if response.status_code == 200:
    surah_data = response.json()['data']
else:
    print("Gagal mengambil data surah")
    exit()

# Masukkan data ke tabel 'surah' dan 'ayah'
for surah in surah_data:
    # Konversi tempat turun ke format yang sesuai dengan ENUM di database
    tempat_turun = surah['tempatTurun']
    tempat_turun_mapped = revelation_mapping.get(tempat_turun, 'Mekah')  # Default ke 'Mekah' jika tidak ditemukan

    surah_entry = Surah(
        id=surah['nomor'],
        name_arabic=surah['nama'],
        name_english=surah['namaLatin'],
        number_of_ayah=surah['jumlahAyat'],
        revelation_place=tempat_turun_mapped,  # Gunakan nilai yang sudah dipetakan
        revelation_order=surah.get('urutanWahyu', 0)
    )
    session.add(surah_entry)
    session.commit()

    # Ambil data ayat per surah
    ayah_response = requests.get(f"https://equran.id/api/v2/surat/{surah['nomor']}")
    if ayah_response.status_code == 200:
        ayah_data = ayah_response.json()['data']['ayat']
        for ayah in ayah_data:
            # Gunakan nilai default None jika juz tidak ditemukan
            juz_number = ayah.get('juz', None)

            # Tambahkan Juz ke tabel jika belum ada
            if juz_number is not None:
                juz_entry = session.query(Juz).filter_by(number=juz_number).first()
                if not juz_entry:
                    juz_entry = Juz(
                        number=juz_number,
                        start_surah=surah['nomor'] if ayah['nomorAyat'] == 1 else None,
                        start_ayah=ayah['nomorAyat'] if ayah['nomorAyat'] == 1 else None
                    )
                    session.add(juz_entry)

            # Insert data ayah
            ayah_entry = Ayah(
                surah_id=surah['nomor'],
                ayah_number=ayah['nomorAyat'],
                text_arabic=ayah['teksArab'],
                text_translation=ayah['teksIndonesia'],
                juz_number=juz_number  # Akan menjadi None jika tidak ada info juz
            )
            session.add(ayah_entry)
        session.commit()
    else:
        print(f"Gagal mengambil data ayat untuk surah {surah['namaLatin']}")

session.close()
print("Data Al-Qur'an berhasil dimasukkan ke database.")
