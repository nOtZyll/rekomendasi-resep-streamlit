import streamlit as st
import pandas as pd
import json
import ast
import re

# Mengatur konfigurasi halaman (harus menjadi perintah pertama Streamlit)
st.set_page_config(
    page_title="Dapur Cerdas: Rekomendasi Resep",
    page_icon="🍳",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Gunakan cache untuk memuat data agar tidak perlu di-load ulang setiap interaksi
@st.cache_data
def muat_data(file_resep, file_aturan):
    """
    Memuat dataset resep dan file aturan asosiasi dengan caching.
    """
    try:
        df_resep = pd.read_csv(file_resep)
        # Menggunakan nama kolom dari kode Anda yang berhasil: 'bahan-bahan'
        df_resep['bahan-bahan'] = df_resep['bahan-bahan'].apply(ast.literal_eval)
        
        with open(file_aturan, 'r') as f:
            aturan_asosiasi = json.load(f)
            
        return df_resep, aturan_asosiasi
    except FileNotFoundError:
        st.error(f"Gagal memuat data. Pastikan file 'master_resep.csv' dan 'aturan_asosiasi_dict.json' ada di folder yang sama dengan aplikasi.")
        return None, None
    except Exception as e:
        st.error(f"Terjadi kesalahan saat memuat data: {e}")
        return None, None

def rekomendasi_resep(bahan_saya, df_resep, aturan_asosiasi, top_n=5):
    """
    Fungsi inti untuk memberikan rekomendasi resep dengan logika saran cerdas yang baru.
    """
    bahan_saya_set = set(bahan.strip().lower() for bahan in bahan_saya)
    hasil_rekomendasi = []

    for index, row in df_resep.iterrows():
        judul_resep = row['judul_resep']
        url_sumber = row['url_sumber'] # Mengambil URL resep
        bahan_resep_set = set(row['bahan-bahan'])
        cluster_persona = row['cluster_persona']

        bahan_cocok = bahan_saya_set.intersection(bahan_resep_set)
        bahan_kurang = bahan_resep_set - bahan_saya_set
        
        if len(bahan_resep_set) > 0:
            skor_cocok = len(bahan_cocok) / len(bahan_resep_set)
        else:
            skor_cocok = 0

        if skor_cocok > 0:
            # --- LOGIKA BARU UNTUK SARAN CERDAS ---
            # Tujuannya adalah menyarankan bahan yang TIDAK ADA di resep ini,
            # tetapi cocok berdasarkan bahan yang dimiliki pengguna untuk resep ini.
            saran_cerdas_list = []
            bahan_disarankan = set() # Untuk menghindari saran duplikat

            for antecedent_str, consequent in aturan_asosiasi.items():
                antecedent = set(antecedent_str.split(','))
                
                # Kondisi 1: Aturan terpicu oleh bahan yang cocok
                # Kondisi 2: Bahan yang disarankan (consequent) BUKAN bagian dari resep asli
                # Kondisi 3: Bahan yang disarankan belum pernah disarankan sebelumnya
                if antecedent.issubset(bahan_cocok) and consequent not in bahan_resep_set and consequent not in bahan_disarankan:
                    saran = f"`{', '.join(antecedent)}` banyak digunakan dengan **`{consequent}`**, Anda mungkin juga tertarik untuk membeli **`{consequent}`** sebagai pelengkap."
                    saran_cerdas_list.append(saran)
                    bahan_disarankan.add(consequent)
                    
                    # Batasi jumlah saran agar tidak terlalu banyak
                    if len(saran_cerdas_list) >= 2:
                        break
            
            rekomendasi = {
                "judul_resep": judul_resep,
                "url_sumber": url_sumber, # Menambahkan URL ke hasil
                "skor_cocok_persen": round(skor_cocok * 100, 2),
                "bahan_kurang": sorted(list(bahan_kurang)),
                "cluster_persona": cluster_persona,
                "saran_cerdas": saran_cerdas_list
            }
            hasil_rekomendasi.append(rekomendasi)

    hasil_rekomendasi_urut = sorted(hasil_rekomendasi, key=lambda x: x['skor_cocok_persen'], reverse=True)
    return hasil_rekomendasi_urut[:top_n]


# --- UI APLIKASI STREAMLIT ---

# Memuat data menggunakan fungsi yang sudah di-cache
df_resep, aturan_asosiasi = muat_data('master_resep.csv', 'aturan_asosiasi_dict.json')

# Tampilan Sidebar
with st.sidebar:
    st.header("🍳 Dapur Cerdas")
    st.info("Aplikasi ini membantu Anda menemukan resep masakan berdasarkan bahan-bahan yang Anda miliki di dapur.")
    
    st.header("Contoh Bahan")
    st.markdown("""
    Coba salin dan tempel contoh di bawah ini ke dalam kotak input:
    - `bawang putih, bawang merah, garam, kecap manis, nasi, merica, telur`
    - `daging sapi, serai, daun salam, jahe, kunyit, garam, bawang merah`
    - `jahe, daun jeruk, bawang putih`
    """)
    st.warning("Pastikan file `master_resep.csv` dan `aturan_asosiasi_dict.json` ada di folder yang sama dengan aplikasi ini.")

# Tampilan Utama
st.title("Sistem Rekomendasi Resep")
st.markdown("Masukkan bahan-bahan yang Anda miliki, pisahkan dengan **koma** atau **baris baru**.")

if df_resep is not None and aturan_asosiasi is not None:
    # Area input untuk pengguna
    input_bahan_str = st.text_area(
        "Masukkan bahan-bahan di sini...",
        height=120,
        placeholder="Contoh: bawang putih, telur, nasi, kecap manis"
    )

    # Tombol untuk memicu rekomendasi
    if st.button("🔍 Cari Resep!", use_container_width=True, type="primary"):
        if input_bahan_str.strip() == "":
            st.warning("Mohon masukkan setidaknya satu bahan.")
        else:
            # Membersihkan input: pisahkan dengan koma atau baris baru, hapus spasi, dan saring item kosong
            bahan_pengguna = [bahan.strip().lower() for bahan in re.split(r'[,\n]', input_bahan_str) if bahan.strip()]
            
            with st.spinner("Mencari resep terbaik untuk Anda..."):
                # Mengubah top_n menjadi 5
                rekomendasi = rekomendasi_resep(bahan_pengguna, df_resep, aturan_asosiasi, top_n=5)

            st.success("Pencarian Selesai!")
            st.markdown("---")
            
            # Menampilkan hasil rekomendasi
            if not rekomendasi:
                st.info("Tidak ada resep yang cukup cocok ditemukan. Coba tambahkan lebih banyak bahan atau periksa kembali penulisan Anda.")
            else:
                st.subheader("Berikut Rekomendasi Resep Teratas Untuk Anda:")
                for i, resep in enumerate(rekomendasi):
                    # Membuat container dengan border untuk setiap resep
                    with st.container(border=True):
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.write(f"**{i+1}. {resep['judul_resep']}**")
                            st.caption(f"Kategori: *{resep['cluster_persona']}*")
                            # Menampilkan link resep
                            st.markdown(f"🔗 [Lihat Resep Lengkap]({resep['url_sumber']})", help="Buka tautan resep di tab baru")
                        with col2:
                            st.metric(label="Kecocokan", value=f"{resep['skor_cocok_persen']}%")
                        
                        # Expander untuk detail
                        with st.expander("Lihat Detail Kebutuhan & Saran"):
                            if resep['bahan_kurang']:
                                st.write("**Bahan yang Perlu Dibeli:**")
                                for bahan in resep['bahan_kurang']:
                                    st.markdown(f"- {bahan}")
                            else:
                                st.success("🎉 Selamat! Anda memiliki semua bahan yang diperlukan.")
                            
                            # Menampilkan Saran Cerdas dengan logika baru
                            if resep['saran_cerdas']:
                                st.write("---") # Pemisah visual
                                st.write("**Rekomendasi Pelengkap:**")
                                for saran in resep['saran_cerdas']:
                                    st.markdown(f"💡 {saran}")
                    st.write("") # Memberi sedikit spasi
