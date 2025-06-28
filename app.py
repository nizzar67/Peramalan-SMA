import streamlit as st
import pandas as pd
import datetime
from sqlalchemy.orm import Session
from database import ActualData, create_data, get_all_data, get_data_by_id, update_data, delete_data, SessionLocal
import sqlalchemy # Import sqlalchemy untuk menangani IntegrityError

# --- Fungsi untuk perhitungan Moving Average ---
def calculate_moving_average(data: pd.DataFrame, window: int):
    if data.empty:
        return pd.Series(dtype=float)
    
    data = data.sort_values(by='date')
    
    return data['value'].rolling(window=window).mean()


# --- Fungsi untuk mendapatkan sesi DB ---
@st.cache_resource
def get_database_session():
    return SessionLocal()

db: Session = get_database_session()

# --- Inisialisasi Session State (PENTING UNTUK FIX INI) ---
if 'delete_confirm_step' not in st.session_state:
    st.session_state.delete_confirm_step = 0 # 0 = Belum mulai, 1 = Menunggu konfirmasi, 2 = Dikonfirmasi

if 'id_to_delete' not in st.session_state:
    st.session_state.id_to_delete = None


# --- Judul Aplikasi ---
st.set_page_config(layout="wide", page_title="Prediksi Moving Average")
st.title("Aplikasi Prediksi Moving Average")

# --- Tabs untuk Navigasi ---
tab1, tab2, tab3 = st.tabs(["Input Data & Prediksi", "Kelola Data Aktual", "Tentang"])

with tab1:
    st.header("Input Data Aktual & Lihat Prediksi Moving Average")

    # Form untuk input data baru
    with st.form("data_input_form"):
        st.subheader("Tambah Data Baru")
        input_date = st.date_input("Tanggal", datetime.date.today(), key="input_date")
        input_value = st.number_input("Nilai Aktual", min_value=0.0, format="%.2f", key="input_value")
        submitted = st.form_submit_button("Tambah Data")

        if submitted:
            try:
                create_data(db, input_date, input_value)
                st.success(f"Data {input_date} dengan nilai {input_value} berhasil ditambahkan!")
                st.rerun() 
            except sqlalchemy.exc.IntegrityError:
                db.rollback() 
                st.error("Tanggal ini sudah ada. Harap masukkan tanggal yang berbeda atau edit data yang sudah ada.")
            except Exception as e:
                db.rollback()
                st.error(f"Terjadi kesalahan saat menambahkan data: {e}")

    st.markdown("---")

    # Tampilkan data aktual yang sudah ada
    st.subheader("Data Aktual Tersimpan")
    all_actual_data_objects = get_all_data(db)
    
    if all_actual_data_objects:
        data_df = pd.DataFrame([{"id": d.id, "date": d.date, "value": d.value} for d in all_actual_data_objects])
        st.dataframe(data_df, use_container_width=True, hide_index=True)

        # Opsi untuk Moving Average
        st.markdown("---")
        st.subheader("Prediksi Moving Average")
        
        col_ma_1, col_ma_2, col_ma_3 = st.columns(3) # Tambah 1 kolom lagi untuk filter bulan
        with col_ma_1:
            ma_window = st.slider("Pilih Periode Moving Average", min_value=2, max_value=30, value=7)
        with col_ma_2:
            # Dropdown untuk memilih bulan
            # Buat daftar unik bulan dari data yang ada
            if not data_df.empty:
                data_df['date'] = pd.to_datetime(data_df['date'])
                unique_months_years = sorted(list(set(data_df['date'].dt.strftime('%B %Y'))))
                selected_month_year = st.selectbox("Pilih Bulan Prediksi", options=['Semua Bulan'] + unique_months_years, index=0)
            else:
                selected_month_year = 'Semua Bulan' # Default jika tidak ada data
                st.info("Tidak ada data untuk memfilter bulan.")


        with col_ma_3: # Kolom ketiga untuk tombol hitung
            st.write("") 
            st.write("")
            calculate_button = st.button("Hitung Prediksi")

        if calculate_button:
            if len(data_df) >= ma_window:
                # Pastikan kolom 'date' bertipe datetime sebelum perhitungan
                data_df['date'] = pd.to_datetime(data_df['date'])
                data_df['MA'] = calculate_moving_average(data_df, ma_window) 
                
                # Filter data berdasarkan bulan yang dipilih
                if selected_month_year != 'Semua Bulan':
                    # Ambil bulan dan tahun dari string pilihan
                    month_name, year = selected_month_year.rsplit(' ', 1)
                    # Konversi nama bulan ke nomor bulan
                    month_number = datetime.datetime.strptime(month_name, '%B').month
                    
                    filtered_df = data_df[
                        (data_df['date'].dt.month == month_number) & 
                        (data_df['date'].dt.year == int(year))
                    ].copy() # Gunakan .copy() untuk menghindari SettingWithCopyWarning
                else:
                    filtered_df = data_df.copy()

                if not filtered_df.empty:
                    st.subheader(f"Hasil SMA (Periode {ma_window}) untuk {selected_month_year}") 
                    st.dataframe(filtered_df.fillna("N/A"), use_container_width=True, hide_index=True) 

                    st.subheader(f"Grafik Data Aktual dan Moving Average untuk {selected_month_year}")
                    st.line_chart(filtered_df.set_index('date')[['value', 'MA']])
                else:
                    st.warning(f"Tidak ada data untuk bulan {selected_month_year} setelah perhitungan SMA.")
            else:
                st.warning(f"Tidak cukup data untuk menghitung SMA dengan periode {ma_window}. Anda membutuhkan setidaknya {ma_window} data.")
    else:
        st.info("Belum ada data aktual yang tersimpan. Silakan masukkan data di atas.")

with tab2:
    st.header("Kelola Data Aktual")

    st.subheader("Edit Data")
    edit_data_id = st.number_input("ID Data yang akan Diedit", min_value=1, format="%d", key="edit_id")
    
    data_to_edit = get_data_by_id(db, edit_data_id)
    
    with st.form("edit_data_form"):
        if data_to_edit:
            st.write(f"Mengedit data dengan ID: **{data_to_edit.id}** (Tanggal: {data_to_edit.date}, Nilai: {data_to_edit.value})")
            edited_date = st.date_input("Tanggal Baru", data_to_edit.date, key="edited_date")
            edited_value = st.number_input("Nilai Baru", value=data_to_edit.value, min_value=0.0, format="%.2f", key="edited_value")
            edit_submitted = st.form_submit_button("Perbarui Data")

            if edit_submitted:
                try:
                    updated = update_data(db, edit_data_id, edited_date, edited_value)
                    if updated:
                        st.success(f"Data ID {edit_data_id} berhasil diperbarui!")
                        st.rerun() 
                    else:
                        st.error("Gagal memperbarui data. ID tidak ditemukan.")
                except sqlalchemy.exc.IntegrityError:
                    db.rollback() 
                    st.error("Tanggal ini sudah ada untuk data lain. Harap masukkan tanggal yang berbeda.")
                except Exception as e:
                    db.rollback() 
                    st.error(f"Terjadi kesalahan saat memperbarui data: {e}")
        else:
            st.info("Masukkan ID Data yang valid untuk diedit.")
        
    st.markdown("---")

    st.subheader("Hapus Data")
    
    delete_data_id_input = st.number_input("ID Data yang akan Dihapus", min_value=1, format="%d", key="delete_id_input")
    
    if st.button("Hapus Data", key="delete_button_trigger"):
        if get_data_by_id(db, delete_data_id_input): 
            st.session_state.delete_confirm_step = 1
            st.session_state.id_to_delete = delete_data_id_input
            st.rerun() 
        else:
            st.error("ID Data tidak ditemukan. Tidak ada yang bisa dihapus.")
            st.session_state.delete_confirm_step = 0 

    if st.session_state.delete_confirm_step == 1:
        st.warning(f"Anda akan menghapus data dengan ID: **{st.session_state.id_to_delete}**. Tindakan ini tidak bisa dibatalkan.")
        confirm_delete_checkbox = st.checkbox("Saya yakin ingin menghapus data ini?", key="confirm_delete_checkbox")
        
        if confirm_delete_checkbox:
            deleted = delete_data(db, st.session_state.id_to_delete)
            if deleted:
                st.success(f"Data ID {st.session_state.id_to_delete} berhasil dihapus!")
                st.session_state.delete_confirm_step = 0 
                st.session_state.id_to_delete = None
                st.rerun() 
            else:
                st.error("Gagal menghapus data. ID tidak ditemukan (mungkin sudah dihapus oleh sesi lain).")
                st.session_state.delete_confirm_step = 0 
                st.session_state.id_to_delete = None
                st.rerun() 
    elif st.session_state.delete_confirm_step == 2:
        st.session_state.delete_confirm_step = 0 

with tab3:
    st.header("Tentang Aplikasi Ini")
    st.write("""
    Aplikasi ini dibuat untuk membantu Anda memprediksi nilai menggunakan metode **Simple Moving Average (SMA)**.
    Anda dapat memasukkan data aktual, menyimpannya, mengedit, atau menghapusnya, dan kemudian menggunakan data tersebut
    untuk melihat tren dengan berbagai periode *moving average*.
    """)
    st.subheader("Fitur:")
    st.markdown("""
    * **Input Data:** Masukkan tanggal dan nilai aktual.
    * **Penyimpanan Data:** Data Anda akan tersimpan dalam database SQLite dan dapat digunakan kembali.
    * **Kelola Data:** Mudah untuk mengedit atau menghapus data yang sudah ada.
    * **Prediksi Simple Moving Average (SMA):** Hitung dan visualisasikan SMA.
    * **Filter Bulan:** Lihat hasil prediksi untuk bulan tertentu.
    """)
    st.subheader("Cara Penggunaan:")
    st.markdown("""
    1.  Buka tab **"Input Data & Prediksi"**.
    2.  Gunakan formulir **"Tambah Data Baru"** untuk memasukkan data tanggal dan nilai aktual.
    3.  Data yang sudah ada akan ditampilkan di bawah.
    4.  Pilih **"Periode Moving Average"** dan **"Pilih Bulan Prediksi"**, lalu klik **"Hitung Prediksi"** untuk melihat hasilnya.
    5.  Untuk mengelola data (edit/hapus), buka tab **"Kelola Data Aktual"**.
    """)