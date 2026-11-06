"""MSP430 Simulator CLI and Launcher helpers."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .asm import assemble
from .cpu import MSP430

HELP_TEXT = """MSP430 Simulator (G2553)
Kullanim:
  python3 run.py                        GUI'yi baslatir
  python3 run.py <dosya.asm>            Belirtilen assembly dosyasini acarak GUI'yi baslatir
  python3 run.py --cli <dosya.asm>      Terminalde calistirir (GUI gerektirmez)
  python3 run.py --assemble <dosya.asm> Assembly kodunu derler ve sonucu gosterir
  python3 run.py --help                 Bu yardim mesajini gosterir

Secenekler:
  -c, --cli <dosya>     Terminalde simule et (GUI acmaz)
  -a, --assemble <dosya> Kodun makine kodu karsiligini ve hatalarini listele
  --cycles <sayi>       CLI modunda calistirilacak maksimum cycle sayisi (varsayilan: 100000)
  -h, --help            Yardim mesajini goster
"""


def find_tk_python():
    """Tkinter destekli Python yorumlayicisini bulur."""
    candidates = [
        sys.executable,
        '/usr/local/bin/python3',
        '/usr/bin/python3',
        shutil.which('python3.13'),
        shutil.which('python3.12'),
        shutil.which('python3.11'),
        shutil.which('python3.10'),
        shutil.which('python3'),
    ]
    seen = set()
    for c in candidates:
        if not c or c in seen:
            continue
        seen.add(c)
        try:
            res = subprocess.run([c, '-c', 'import tkinter'], capture_output=True, timeout=2)
            if res.returncode == 0:
                return c
        except Exception:
            continue
    return None


def run_cli(args=None):
    """
    CLI komutlarini isler.
    Dondurur: (cikis_kodu, cikti_metni)
    Eger GUI acilmasi gerekiyorsa cikis_kodu = -1, cikti_metni = acilacak_dosya_yolu (veya None).
    """
    if args is None:
        args = sys.argv[1:]

    if not args:
        return -1, None

    if '-h' in args or '--help' in args:
        return 0, HELP_TEXT

    cycles = 100000
    if '--cycles' in args:
        idx = args.index('--cycles')
        if idx + 1 < len(args) and args[idx + 1].isdigit():
            cycles = int(args[idx + 1])
            args = args[:idx] + args[idx + 2:]

    # --assemble modu
    if '-a' in args or '--assemble' in args:
        flag = '-a' if '-a' in args else '--assemble'
        idx = args.index(flag)
        if idx + 1 >= len(args):
            return 1, 'Hata: --assemble icin bir assembly dosyasi belirtilmelidir.'
        target = Path(args[idx + 1])
        if not target.is_file():
            return 1, f'Hata: Dosya bulunamadi: {target}'
        text = target.read_text(encoding='utf-8', errors='replace')
        res = assemble(text)
        if res.errors:
            lines = [f'Hata: {len(res.errors)} hata bulundu:']
            for no, err in res.errors:
                lines.append(f'  Satir {no}: {err}')
            return 1, '\n'.join(lines)
        lines = [f'Assemble basarili ({len(res.image)} bellek bloku):']
        for start_addr, data in sorted(res.image.items()):
            end_addr = start_addr + len(data) - 1
            lines.append(f'  0x{start_addr:04X} - 0x{end_addr:04X} ({len(data)} bayt)')
        if res.warnings:
            lines.append('\nUyarilar:')
            for no, w in res.warnings:
                lines.append(f'  Satir {no}: {w}')
        return 0, '\n'.join(lines)

    # --cli modu
    if '-c' in args or '--cli' in args:
        flag = '-c' if '-c' in args else '--cli'
        idx = args.index(flag)
        if idx + 1 >= len(args):
            return 1, 'Hata: --cli icin bir assembly dosyasi belirtilmelidir.'
        target = Path(args[idx + 1])
        if not target.is_file():
            return 1, f'Hata: Dosya bulunamadi: {target}'
        text = target.read_text(encoding='utf-8', errors='replace')
        res = assemble(text)
        if res.errors:
            lines = [f'Assemble hatasi ({len(res.errors)} hata):']
            for no, err in res.errors:
                lines.append(f'  Satir {no}: {err}')
            return 1, '\n'.join(lines)
        cpu = MSP430()
        cpu.load(res.image)
        stop_reason = cpu.run(cycles)
        sr = cpu.r[2]
        lines = [
            f'Durum: {stop_reason} | Cycles: {cpu.cycles} | Komut: {cpu.icount}',
            f'PC: 0x{cpu.r[0]:04X}  SP: 0x{cpu.r[1]:04X}  SR: 0x{sr:04X} (V={sr>>8&1} N={sr>>2&1} Z={sr>>1&1} C={sr&1})',
            f'R4: 0x{cpu.r[4]:04X}  R5: 0x{cpu.r[5]:04X}  R6: 0x{cpu.r[6]:04X}  R7: 0x{cpu.r[7]:04X}',
            f'R8: 0x{cpu.r[8]:04X}  R9: 0x{cpu.r[9]:04X}  R10: 0x{cpu.r[10]:04X}  R11: 0x{cpu.r[11]:04X}',
            f'R12: 0x{cpu.r[12]:04X}  R13: 0x{cpu.r[13]:04X}  R14: 0x{cpu.r[14]:04X}  R15: 0x{cpu.r[15]:04X}',
        ]
        if cpu.uart.out:
            lines.append(f"UART cikisi: {bytes(cpu.uart.out).decode('latin-1', 'replace')!r}")
        if cpu.log:
            lines.append(f'Son loglar: {cpu.log[-3:]}')
        return 0, '\n'.join(lines)

    # Diger argumanlar: dosya yolu kabul edilir ve GUI ile acilir
    first = args[0]
    if Path(first).is_file():
        return -1, str(Path(first).resolve())

    return 1, f'Bilinmeyen secenek veya dosya bulunamadi: {first}\nYardim icin: --help'
