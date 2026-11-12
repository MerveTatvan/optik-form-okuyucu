"""Optik formun sabit (kanonik) yerleşimi.

Form üretici (formgen.py) ve okuyucu (reader.py) AYNI sabitleri kullanır.
Formu değiştirmek istersen (soru sayısı, şık sayısı vb.) sadece bu dosyayı düzenle.

Tüm değerler piksel cinsindendir ve A4 oranında (1000 x 1414) bir tuval içindir.
"""

# Kanonik form boyutu (A4 oranı 1 : 1.414)
FORM_W, FORM_H = 1000, 1414

# Dört köşedeki siyah kare işaretçiler (hizalama için). Sıra: SolÜst, SağÜst, SağAlt, SolAlt
MARKER_SIZE = 40
MARKER_CENTERS = ((50, 50), (950, 50), (950, 1364), (50, 1364))

# Formun yönünü (baş aşağı / yan çevrilmiş) anlamak için sol üst köşenin yanındaki siyah çubuk
ORIENT_BAR_CENTER = (135, 50)
ORIENT_BAR_SIZE = (70, 16)

# Cevap alanı
OPTIONS = "ABCDE"
NUM_QUESTIONS = 40
QUESTIONS_PER_COLUMN = 20
BUBBLE_RADIUS = 12

ANSWER_X0 = (170, 630)   # Her sütundaki ilk şıkkın (A) merkez x'i
ANSWER_X_STEP = 50       # Şıklar arası yatay mesafe
ANSWER_Y0 = 680          # İlk sorunun merkez y'si
ANSWER_Y_STEP = 33       # Sorular arası dikey mesafe

# Öğrenci numarası alanı (ID_DIGITS hane, her hane için 0-9 balonu)
ID_DIGITS = 8
ID_X0 = 130
ID_X_STEP = 46
ID_Y0 = 260
ID_Y_STEP = 34


def answer_bubble_center(q: int, opt: int) -> tuple[int, int]:
    """q: 0 tabanlı soru indeksi, opt: 0 tabanlı şık indeksi (A=0)."""
    col, row = divmod(q, QUESTIONS_PER_COLUMN)
    return ANSWER_X0[col] + opt * ANSWER_X_STEP, ANSWER_Y0 + row * ANSWER_Y_STEP


def id_bubble_center(pos: int, digit: int) -> tuple[int, int]:
    """pos: soldan 0 tabanlı hane, digit: 0-9."""
    return ID_X0 + pos * ID_X_STEP, ID_Y0 + digit * ID_Y_STEP
