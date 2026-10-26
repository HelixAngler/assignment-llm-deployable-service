"""
Modul Tools — fungsi-fungsi "aksi" yang dipanggil router ketika intent
BUKAN pertanyaan informasi/kebijakan, melainkan permintaan spesifik
yang butuh pengecekan data langsung (bukan retrieval semantik).

Pola ini mengikuti konsep Tool Integration di Sesi 12.3.
"""

import pandas as pd

MOCK_TICKETS_PATH = "data/mock_tickets.csv"


def get_ticket_status(ticket_id: str) -> str:
    """
    Mencari status tiket berdasarkan ticket_id pada data mock_tickets.csv.

    # TODO: implementasikan pencarian data tiket berdasarkan ticket_id.
    # Jika ticket_id tidak ditemukan, kembalikan pesan yang informatif
    # (bukan error yang membuat aplikasi crash).
    #
    # Contoh langkah:
    #   1. Muat mock_tickets.csv menggunakan pandas
    #   2. Cari baris dengan ticket_id yang cocok
    #   3. Jika ditemukan, susun string jawaban (subject, status, last_update)
    #   4. Jika tidak ditemukan, kembalikan pesan bahwa tiket tidak ditemukan
    """
    df = pd.read_csv(MOCK_TICKETS_PATH)

    normalized_id = (ticket_id or "").strip().upper()
    if not normalized_id:
        return (
            "Saya tidak dapat mengenali ID tiket dari permintaan Anda. "
            "Sebutkan ID tiket dengan format TICKET-XXXX, misalnya TICKET-0001."
        )

    matched = df[df["ticket_id"].str.strip().str.upper() == normalized_id]
    if matched.empty:
        return (
            f"Tiket dengan ID {normalized_id} tidak ditemukan. "
            "Periksa kembali format ID tiket Anda (contoh: TICKET-0001)."
        )

    ticket = matched.iloc[0]
    return (
        f"Tiket {ticket['ticket_id']} — {ticket['subject']}. "
        f"Kategori: {ticket['category']}. "
        f"Status: {ticket['status']}. "
        f"Terakhir diperbarui: {ticket['last_update']}."
    )
