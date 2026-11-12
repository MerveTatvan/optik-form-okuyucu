"""Optik form okuyucu - komut satırı arayüzü.

Örnekler:
    python main.py generate-form                       # yazdırılacak boş formu üretir
    python main.py demo                                # örnek fotoğraflar üretir ve puanlar
    python main.py grade samples --key data/answer_key.json --debug
    python main.py grade foto.jpg --key data/answer_key.json
"""
import argparse
import csv
import sys
from pathlib import Path

from omr import io
from omr.align import AlignmentError
from omr.formgen import draw_blank_form, make_demo_samples
from omr.grader import load_answer_key
from omr.pipeline import process_image
from omr.reader import ReaderParams

ROOT = Path(__file__).resolve().parent


def answers_string(read_answers) -> str:
    """Okunan cevapları tek satır yap: boş='-', çift işaret='*'."""
    return "".join(a if a else "-" for a in read_answers)


def cmd_generate_form(args):
    out = Path(args.out)
    io.imwrite(out, draw_blank_form(scale=args.scale))
    print(f"Boş form kaydedildi: {out}")
    print("Yazdırırken 'Gerçek boyut / %100' seçin ve köşe karelerinin kesilmediğinden emin olun.")


def cmd_grade(args):
    key = load_answer_key(args.key)
    params = ReaderParams(dark_level=args.dark_level, mark_ratio=args.mark_ratio)
    out_dir = Path(args.out)

    files = []
    for item in args.inputs:
        p = Path(item)
        if p.is_dir():
            files += [f for f in io.list_images(p) if "_sonuc" not in f.stem]
        elif p.is_file():
            files.append(p)
        else:
            print(f"[UYARI] Bulunamadı: {p}")
    if not files:
        sys.exit("İşlenecek görüntü bulunamadı.")

    print(f"Sınav: {key.exam_name or '-'} | {key.n} soru | soru başı {key.points_per_question:g} puan | "
          f"yanlış cezası: {key.wrong_penalty:g}\n")
    rows, failed = [], 0
    for f in files:
        debug_dir = out_dir / "debug" / f.stem if args.debug else None
        try:
            result, read, _, overlay = process_image(f, key, params, debug_dir)
        except (AlignmentError, ValueError) as e:
            failed += 1
            print(f"[HATA] {f.name}: {e}")
            rows.append({"dosya": f.name, "ogrenci_no": "", "dogru": "", "yanlis": "", "bos": "", "cift_isaret": "",
                         "puan": "", "cevaplar": "", "durum": f"HATA: {e}"})
            continue
        io.imwrite(out_dir / f"{f.stem}_sonuc.png", overlay)
        print(f"{f.name:<22} No: {result.student_id:<9} D:{result.n_correct:>2} Y:{result.n_wrong:>2} "
              f"B:{result.n_blank:>2} Cift:{result.n_multiple:>2}  PUAN: {result.score:g}/{result.max_score:g}")
        rows.append({"dosya": f.name, "ogrenci_no": result.student_id, "dogru": result.n_correct,
                     "yanlis": result.n_wrong, "bos": result.n_blank, "cift_isaret": result.n_multiple,
                     "puan": result.score, "cevaplar": answers_string(read.answers[:key.n]), "durum": "OK"})

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "sonuclar.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as fh:     # utf-8-sig: Excel Türkçe karakterleri doğru açar
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter=";")
        w.writeheader()
        w.writerows(rows)
    print(f"\nTamamlandı: {len(files) - failed}/{len(files)} form puanlandı.")
    print(f"CSV: {csv_path}\nGörseller: {out_dir}")


def cmd_demo(args):
    key = load_answer_key(ROOT / "data" / "answer_key.json")
    samples = ROOT / "samples"
    io.imwrite(ROOT / "forms" / "bos_form.png", draw_blank_form(scale=2))
    paths = make_demo_samples("".join(key.answers), samples)
    print(f"{len(paths)} örnek fotoğraf üretildi: {samples}\n")
    args.inputs = [str(p) for p in paths]
    args.key = str(ROOT / "data" / "answer_key.json")
    args.out = str(ROOT / "outputs")
    args.dark_level, args.mark_ratio, args.debug = ReaderParams.dark_level, ReaderParams.mark_ratio, True
    cmd_grade(args)


def build_parser():
    ap = argparse.ArgumentParser(description="Optik form okuma ve otomatik puanlama (OpenCV)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate-form", help="Boş optik formu PNG olarak üret")
    g.add_argument("--out", default="forms/bos_form.png")
    g.add_argument("--scale", type=int, default=2, help="Çözünürlük çarpanı (2 = 2000x2828 px)")
    g.set_defaults(func=cmd_generate_form)

    r = sub.add_parser("grade", help="Fotoğraf/tarama dosyalarını puanla")
    r.add_argument("inputs", nargs="+", help="Görüntü dosyaları ve/veya klasörler")
    r.add_argument("--key", default="data/answer_key.json", help="Cevap anahtarı JSON dosyası")
    r.add_argument("--out", default="outputs", help="Çıktı klasörü")
    r.add_argument("--debug", action="store_true", help="Ara adım görsellerini kaydet")
    r.add_argument("--dark-level", type=int, default=ReaderParams.dark_level, help="Koyu piksel eşiği (0-255)")
    r.add_argument("--mark-ratio", type=float, default=ReaderParams.mark_ratio, help="İşaretli sayılma oranı (0-1)")
    r.set_defaults(func=cmd_grade)

    d = sub.add_parser("demo", help="Örnek fotoğrafları üret ve puanla")
    d.set_defaults(func=cmd_demo)
    return ap


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = build_parser().parse_args()
    args.func(args)
