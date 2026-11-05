'''Anotador local YOLO (PT/EN) para orelhas de gatos.

Dependencia: pip install pillow
Execute em TCC: python anotador_orelhas.py
Estrutura: Dataset/**/imagem.jpg -> anotacoes_orelhas/**/imagem.txt
'''
from pathlib import Path
import tkinter as tk
from PIL import Image, ImageTk

BASE_DIR = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()

IMAGES_DIR = BASE_DIR / "Dataset"
LABELS_DIR = BASE_DIR / "anotacoes_orelhas"

EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

print("Projeto:", BASE_DIR)
print("Imagens:", IMAGES_DIR)
print("Anotações:", LABELS_DIR)


IMAGES_DIR = BASE_DIR / "Dataset"
LABELS_DIR = BASE_DIR / "anotacoes_orelhas"
EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
CLASSES = ("orelha_marcada", "orelha_normal")
CLASS_COLORS = ("#EC407A", "#7465D9")
PINK_BG = "#FFE9F3"
PINK_PANEL = "#FFD4E8"
PINK_LIGHT = "#FFF5FA"
PINK_BUTTON = "#F5A5CE"
PINK_TEXT = "#782A57"
PINK_ACCENT = "#CA3E85"


class EarAnnotator:
    def __init__(self, root):
        self.root = root
        root.title("🐱💗 Anotador de Orelhas / Cat Ear Annotator 💗🐱")
        root.configure(bg=PINK_BG)
        root.geometry("1200x840")
        root.minsize(700, 500)
        self.images = sorted(p for p in IMAGES_DIR.rglob("*") if p.is_file() and p.suffix.lower() in EXTS)
        if not self.images:
            self.popup("Sem fotos / No images", f"Nenhuma imagem em / No images in:\n{IMAGES_DIR}")
            return
        self.index = 0
        self.selected = tk.IntVar(value=0)
        self.boxes = []
        self.dirty = False
        self.original = None
        self.tk_photo = None
        self.base_fit = 1.0
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.drag_start = None
        self.drag_now = None
        self.pan_start = None
        self.canvas_w = 800
        self.canvas_h = 480
        self._resize_job = None
        self.make_ui()
        self.bind_keys()
        self.load_image()
        self.root.after(200, self._initial_focus)

    def button(self, parent, text, action, strong=False):
        return tk.Button(parent, text=text, command=action, bg=PINK_ACCENT if strong else PINK_BUTTON,
                         fg="white" if strong else PINK_TEXT, activebackground="#E879B1",
                         activeforeground="white", relief="flat", cursor="hand2", bd=0,
                         padx=10, pady=7, font=("Segoe UI", 10, "bold"))

    def make_ui(self):
        header = tk.Frame(self.root, bg=PINK_BG)
        header.pack(fill="x", padx=10, pady=(7, 1))
        tk.Label(header, text="🐾💖 Orelhas de Gatos / Cat Ears 💖🐾", bg=PINK_BG,
                 fg=PINK_ACCENT, font=("Segoe UI", 17, "bold")).pack()
        tk.Label(header, text="Marque a orelha inteira / Draw a box around the whole ear",
                 bg=PINK_BG, fg=PINK_TEXT, font=("Segoe UI", 10)).pack()

        toolbar = tk.Frame(self.root, bg=PINK_LIGHT)
        toolbar.pack(fill="x", padx=10, pady=5)
        radio = tk.Frame(toolbar, bg=PINK_LIGHT)
        radio.pack(fill="x", padx=5, pady=(5, 0))
        for idx, text in enumerate(("🎀 0 — Marcada / Marked (corte ou tatuagem / tip or tattoo)",
                                    "🌸 1 — Normal / Unmarked")):
            tk.Radiobutton(radio, text=text, value=idx, variable=self.selected,
                           bg=PINK_LIGHT, fg=CLASS_COLORS[idx], activebackground=PINK_LIGHT,
                           selectcolor=PINK_BG, font=("Segoe UI", 10, "bold")).pack(side="left", padx=8)

        actions = tk.Frame(toolbar, bg=PINK_LIGHT)
        actions.pack(fill="x", padx=5, pady=5)
        items = [
            ("↶ Desfazer / Undo (Z)", self.undo),
            ("💾 Salvar / Save (S)", self.save),
            ("🐾 Sem orelha / No ear", self.save_no_ear),
            ("◀ Anterior / Previous", self.prev_image),
            ("Próxima / Next ▶", self.next_image),
            ("− Zoom", lambda: self.change_zoom(1 / 1.25)),
            ("+ Zoom", lambda: self.change_zoom(1.25)),
            ("⤢ Ajustar / Fit (F)", self.fit_image),
        ]
        for i, (name, fn) in enumerate(items):
            self.button(actions, name, fn, strong=(i == 1)).pack(side="left", padx=3, pady=2)

        # Busca rápida: nome, prefixo ou caminho relativo.
        search_frame = tk.Frame(self.root, bg=PINK_PANEL)
        search_frame.pack(fill="x", padx=10, pady=(0, 5))
        tk.Label(search_frame, text="🔎 Buscar foto / Find image:",
                 bg=PINK_PANEL, fg=PINK_TEXT, font=("Segoe UI", 10, "bold")
                 ).pack(side="left", padx=(10, 6), pady=7)
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                                     bg=PINK_LIGHT, fg=PINK_TEXT, insertbackground=PINK_TEXT,
                                     font=("Segoe UI", 11), relief="flat")
        self.search_entry.pack(side="left", fill="x", expand=True, ipady=5, padx=4)
        self.search_entry.bind("<Return>", self._search_enter)
        self.search_entry.bind("<Escape>", self._leave_search)
        self.button(search_frame, "🔍 Procurar / Search", self.search_images,
                    strong=True).pack(side="left", padx=7)

        self.status = tk.Label(self.root, bg=PINK_PANEL, fg=PINK_TEXT, anchor="w",
                               justify="left", font=("Segoe UI", 10), padx=12, pady=5)
        self.status.pack(fill="x", padx=10, pady=(0, 5))
        self.key_status_var = tk.StringVar(value="⌨ Teclado: clique na foto e pressione 0, 1, Z, F, S ou as setas")
        self.key_status = tk.Label(self.root, textvariable=self.key_status_var,
                                   bg=PINK_LIGHT, fg=PINK_TEXT, anchor="w",
                                   padx=12, pady=5, font=("Segoe UI", 10, "bold"))
        self.key_status.pack(fill="x", padx=10, pady=(0, 5))

        self.canvas = tk.Canvas(self.root, bg="#FFF8FC", bd=0, highlightthickness=2,
                                takefocus=True,
                                highlightbackground="#EEA8CF", cursor="crosshair")
        self.canvas.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.canvas.bind("<Configure>", self.on_resize)
        self.canvas.bind("<ButtonPress-1>", self.mouse_down)
        self.canvas.bind("<B1-Motion>", self.mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.mouse_up)
        self.canvas.bind("<ButtonPress-3>", self.pan_down)
        self.canvas.bind("<B3-Motion>", self.pan_move)
        self.canvas.bind("<ButtonRelease-3>", lambda e: setattr(self, "pan_start", None))
        self.canvas.bind("<MouseWheel>", self.wheel)
        self.canvas.bind("<Button-4>", lambda e: self.change_zoom(1.2, e.x, e.y))
        self.canvas.bind("<Button-5>", lambda e: self.change_zoom(1 / 1.2, e.x, e.y))

    def _search_enter(self, event=None):
        self.search_images()
        return "break"

    def _leave_search(self, event=None):
        self.canvas.focus_set()
        return "break"

    def _initial_focus(self):
        # Chamar após a janela estar desenhada para o foco funcionar no Windows.
        if self.root.winfo_exists():
            self.root.lift()
            self.canvas.focus_set()

    def _click_focus(self, event):
        """Qualquer clique fora da pesquisa transfere o foco ao canvas."""
        widget = event.widget
        if widget.winfo_toplevel() != self.root:
            return
        if widget == self.search_entry:
            return
        self.root.after_idle(self._focus_canvas_if_not_search)

    def _focus_canvas_if_not_search(self):
        if not self.canvas.winfo_exists():
            return
        # Não interferir no diálogo modal (salvar/descartar).
        focused = self.root.focus_get()
        if focused is not None and focused.winfo_toplevel() != self.root:
            return
        self.canvas.focus_set()

    def _shortcut_status(self, description):
        self.key_status_var.set(f"⌨ Atalho reconhecido: {description}")
        print(f"[ATALHO] {description}", flush=True)

    def _key_handler(self, event):
        """Recebe tecla antes dos handlers padrão dos outros widgets."""
        widget = event.widget
        if widget.winfo_toplevel() != self.root:
            return
        if widget == self.search_entry:
            return

        key = event.keysym.lower()
        control = bool(event.state & 0x0004)
        alt = bool(event.state & 0x0008)
        if alt:
            return
        if control and key not in {"s", "z", "f"}:
            return

        actions = {
            "s": ("S: salvar", self.save),
            "z": ("Z: desfazer", self.undo),
            "f": ("F: ajustar", self.fit_image),
            "0": ("0: marcada", lambda: self.selected.set(0)),
            "1": ("1: normal", lambda: self.selected.set(1)),
            "kp_0": ("0: marcada", lambda: self.selected.set(0)),
            "kp_1": ("1: normal", lambda: self.selected.set(1)),
            "left": ("Seta esquerda: anterior", self.prev_image),
            "right": ("Seta direita: próxima", self.next_image),
            "plus": ("+: ampliar", lambda: self.change_zoom(1.25)),
            "equal": ("+: ampliar", lambda: self.change_zoom(1.25)),
            "kp_add": ("+: ampliar", lambda: self.change_zoom(1.25)),
            "minus": ("-: reduzir", lambda: self.change_zoom(1 / 1.25)),
            "kp_subtract": ("-: reduzir", lambda: self.change_zoom(1 / 1.25)),
        }
        found = actions.get(key)
        if found:
            description, action = found
            self._shortcut_status(description)
            action()
            return "break"

    def _install_shortcut_tag(self, widget):
        """Insere handler de teclado ANTES do handler padrão de cada widget."""
        if widget != self.search_entry and widget.winfo_toplevel() == self.root:
            tags = widget.bindtags()
            if "EarShortcuts" not in tags:
                widget.bindtags(("EarShortcuts",) + tags)
        for child in widget.winfo_children():
            self._install_shortcut_tag(child)

    def bind_keys(self):
        # Handler com prioridade alta. A busca não recebe esse bindtag.
        self.root.bind_class("EarShortcuts", "<KeyPress>", self._key_handler)
        self._install_shortcut_tag(self.root)
        # Se o campo de busca ainda estiver em foco e clicar fora, devolve foco.
        self.root.bind_all("<ButtonPress-1>", self._click_focus, add="+")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    @property
    def current(self):
        return self.images[self.index]

    @property
    def label_path(self):
        return LABELS_DIR / self.current.relative_to(IMAGES_DIR).with_suffix(".txt")

    def popup(self, title, msg):
        """Diálogo próprio com fundo rosa, inclusive para confirmação de salvamento."""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.configure(bg=PINK_BG)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        tk.Label(dialog, text="🐱 💗 🐾", bg=PINK_BG, fg=PINK_ACCENT,
                 font=("Segoe UI", 22, "bold")).pack(pady=(15, 3))
        tk.Label(dialog, text=msg, bg=PINK_BG, fg=PINK_TEXT, font=("Segoe UI", 11),
                 wraplength=410, justify="center", padx=22).pack(pady=8)
        self.button(dialog, "OK 💗", dialog.destroy, strong=True).pack(pady=(5, 18))
        dialog.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(0,x)}+{max(0,y)}")
        dialog.grab_set()
        dialog.wait_window()

    def question(self):
        result = {"value": None}
        dialog = tk.Toplevel(self.root)
        dialog.title("🐱 Alterações / Unsaved changes")
        dialog.configure(bg=PINK_BG)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        tk.Label(dialog, text="💗 Salvar antes de continuar?\nSave before continuing?",
                 bg=PINK_BG, fg=PINK_TEXT, font=("Segoe UI", 12, "bold"),
                 padx=30, pady=20).pack()
        row = tk.Frame(dialog, bg=PINK_BG)
        row.pack(padx=14, pady=(0, 15))
        def done(v):
            result["value"] = v
            dialog.destroy()
        for label, val in (("Salvar / Save", True), ("Descartar / Discard", False), ("Cancelar / Cancel", None)):
            self.button(row, label, lambda v=val: done(v)).pack(side="left", padx=4)
        dialog.protocol("WM_DELETE_WINDOW", lambda: done(None))
        dialog.grab_set()
        dialog.wait_window()
        return result["value"]

    def load_image(self):
        self.boxes = []
        self.dirty = False
        with Image.open(self.current) as im:
            # Manter dimensões e coordenadas originais para compatibilidade YOLO.
            self.original = im.convert("RGB")
        if self.label_path.exists():
            for line in self.label_path.read_text(encoding="utf-8").splitlines():
                fields = line.split()
                if len(fields) != 5:
                    continue
                try:
                    cls = int(fields[0])
                    coords = tuple(map(float, fields[1:]))
                    if cls in (0, 1):
                        self.boxes.append((cls, *coords))
                except ValueError:
                    pass
        self.root.update_idletasks()
        self.canvas_w = max(100, self.canvas.winfo_width())
        self.canvas_h = max(100, self.canvas.winfo_height())
        self.fit_image()

    def on_resize(self, event):
        self.canvas_w = max(1, event.width)
        self.canvas_h = max(1, event.height)
        if self._resize_job is not None:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(100, self.fit_image)

    def fit_image(self):
        if self.original is None:
            return
        w, h = self.original.size
        self.base_fit = min((self.canvas_w - 20) / w, (self.canvas_h - 20) / h)
        self.zoom = 1.0
        self.pan_x = (self.canvas_w - w * self.base_fit) / 2
        self.pan_y = (self.canvas_h - h * self.base_fit) / 2
        self.render()

    def scale(self):
        return self.base_fit * self.zoom

    def image_to_canvas(self, x, y):
        s = self.scale()
        return x * s + self.pan_x, y * s + self.pan_y

    def canvas_to_image(self, x, y):
        s = self.scale()
        return (x - self.pan_x) / s, (y - self.pan_y) / s

    def on_image(self, x, y):
        ix, iy = self.canvas_to_image(x, y)
        w, h = self.original.size
        return 0 <= ix <= w and 0 <= iy <= h

    def clamp_image(self, x, y):
        ix, iy = self.canvas_to_image(x, y)
        w, h = self.original.size
        return max(0, min(w, ix)), max(0, min(h, iy))

    def render(self):
        if self.original is None:
            return
        self.canvas.delete("all")
        s = self.scale()
        w, h = self.original.size
        rw, rh = max(1, round(w * s)), max(1, round(h * s))
        # Recorta a imagem para a área visível ANTES de converter em PhotoImage.
        # Isso evita alocar imagens enormes quando o zoom é elevado.
        vx1 = max(0, (0 - self.pan_x) / s)
        vy1 = max(0, (0 - self.pan_y) / s)
        vx2 = min(w, (self.canvas_w - self.pan_x) / s)
        vy2 = min(h, (self.canvas_h - self.pan_y) / s)
        if vx2 > vx1 and vy2 > vy1:
            left, top = int(vx1), int(vy1)
            right, bottom = min(w, int(vx2) + 2), min(h, int(vy2) + 2)
            crop = self.original.crop((left, top, right, bottom))
            sw = max(1, round((right - left) * s))
            sh = max(1, round((bottom - top) * s))
            self.tk_photo = ImageTk.PhotoImage(crop.resize((sw, sh), Image.Resampling.LANCZOS))
            ox, oy = self.image_to_canvas(left, top)
            self.canvas.create_image(ox, oy, anchor="nw", image=self.tk_photo)
        else:
            self.tk_photo = None
        for cls, xc, yc, bw, bh in self.boxes:
            x1, y1 = self.image_to_canvas((xc - bw / 2) * w, (yc - bh / 2) * h)
            x2, y2 = self.image_to_canvas((xc + bw / 2) * w, (yc + bh / 2) * h)
            self.canvas.create_rectangle(x1, y1, x2, y2, outline=CLASS_COLORS[cls], width=3)
            self.canvas.create_text(x1 + 4, max(12, y1 - 12), anchor="w",
                                    text=f"{cls}: {CLASSES[cls]}", fill=CLASS_COLORS[cls],
                                    font=("Segoe UI", 10, "bold"))
        if self.drag_start is not None and self.drag_now is not None:
            x1, y1 = self.image_to_canvas(*self.drag_start)
            x2, y2 = self.image_to_canvas(*self.drag_now)
            self.canvas.create_rectangle(x1, y1, x2, y2, outline=CLASS_COLORS[self.selected.get()],
                                         width=2, dash=(5, 3))
        self.status.configure(text=(
            f"📷 Foto / Image: {self.index + 1}/{len(self.images)}  |  {self.current.relative_to(IMAGES_DIR)}\n"
            f"🎀 Caixas / Boxes: {len(self.boxes)}  |  Zoom: {self.zoom:.1f}×  |  "
            f"{'⚠️ Não salvo / Unsaved' if self.dirty else '✅ Salvo / Saved'}\n"
            "🐾 Esquerdo: desenhar / Left: draw  •  Direito: mover / Right: pan  •  "
            "Roda: zoom / Wheel: zoom  •  F: ajustar / fit"
        ))

    def change_zoom(self, factor, x=None, y=None):
        if self.original is None:
            return
        if x is None:
            x = self.canvas_w / 2
        if y is None:
            y = self.canvas_h / 2
        old = self.zoom
        new = max(1.0, min(12.0, old * factor))
        if new == old:
            return
        ix, iy = self.canvas_to_image(x, y)
        self.zoom = new
        self.pan_x = x - ix * self.scale()
        self.pan_y = y - iy * self.scale()
        self.render()

    def wheel(self, event):
        self.change_zoom(1.2 if event.delta > 0 else 1 / 1.2, event.x, event.y)

    def mouse_down(self, event):
        self.canvas.focus_set()
        if self.on_image(event.x, event.y):
            self.drag_start = self.clamp_image(event.x, event.y)
            self.drag_now = self.drag_start

    def mouse_move(self, event):
        if self.drag_start is not None:
            self.drag_now = self.clamp_image(event.x, event.y)
            self.render()

    def mouse_up(self, event):
        if self.drag_start is None:
            return
        xa, ya = self.drag_start
        xb, yb = self.clamp_image(event.x, event.y)
        self.drag_start = None
        self.drag_now = None
        x1, x2 = sorted((xa, xb))
        y1, y2 = sorted((ya, yb))
        if x2 - x1 >= 3 and y2 - y1 >= 3:
            w, h = self.original.size
            self.boxes.append((self.selected.get(), (x1 + x2) / (2 * w),
                               (y1 + y2) / (2 * h), (x2 - x1) / w, (y2 - y1) / h))
            self.dirty = True
        self.render()

    def pan_down(self, event):
        self.pan_start = (event.x, event.y, self.pan_x, self.pan_y)

    def pan_move(self, event):
        if self.pan_start:
            sx, sy, ox, oy = self.pan_start
            self.pan_x = ox + event.x - sx
            self.pan_y = oy + event.y - sy
            self.render()

    def undo(self):
        if self.boxes:
            self.boxes.pop()
            self.dirty = True
            self.render()

    def save(self, show_popup=True):
        self.label_path.parent.mkdir(parents=True, exist_ok=True)
        text = "".join(f"{cls} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}\n" for cls, xc, yc, bw, bh in self.boxes)
        self.label_path.write_text(text, encoding="utf-8")
        self.dirty = False
        self.render()
        if show_popup:
            self.popup("💗 Salvo / Saved", "🐱 Anotações salvas com sucesso!\nAnnotations saved successfully! 💖")

    def save_no_ear(self):
        if self.boxes:
            self.popup("Atenção / Attention", "Esta imagem tem caixas. Use Desfazer antes de marcar sem orelha.\nThis image has boxes. Undo before marking no ear.")
            return
        self.save(show_popup=True)

    def confirm_change(self):
        if not self.dirty:
            return True
        result = self.question()
        if result is None:
            return False
        if result:
            self.save(show_popup=False)
        return True

    def next_image(self):
        if self.index < len(self.images) - 1 and self.confirm_change():
            self.index += 1
            self.load_image()

    def prev_image(self):
        if self.index > 0 and self.confirm_change():
            self.index -= 1
            self.load_image()

    def go_to_image(self, target):
        """Ir até uma foto sem perder alterações ainda não salvas."""
        if target == self.index:
            return True
        if not self.confirm_change():
            return False
        self.index = target
        self.load_image()
        self.canvas.focus_set()
        return True

    def search_images(self):
        """Pesquisar por nome, número, prefixo ou caminho da fotografia."""
        query = self.search_var.get().strip().casefold()
        if not query:
            self.popup("🔎 Busca / Search", "Digite um nome, número ou caminho.\nEnter a filename, number or path.")
            self.search_entry.focus_set()
            return
        matches = [(i, p.relative_to(IMAGES_DIR).as_posix())
                   for i, p in enumerate(self.images)
                   if query in p.relative_to(IMAGES_DIR).as_posix().casefold()]
        if not matches:
            self.popup("😿 Sem resultados / No matches",
                       f"Nenhuma fotografia encontrada para: {query}\nNo matching images found.")
            return
        if len(matches) == 1:
            self.go_to_image(matches[0][0])
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("🐱🔎 Resultados / Search results")
        dialog.configure(bg=PINK_BG)
        dialog.geometry("780x440")
        dialog.minsize(500, 280)
        dialog.transient(self.root)
        tk.Label(dialog, text=f"💗 {len(matches)} fotos encontradas / images found",
                 bg=PINK_BG, fg=PINK_ACCENT,
                 font=("Segoe UI", 13, "bold")).pack(padx=12, pady=(12, 6))
        content = tk.Frame(dialog, bg=PINK_BG)
        content.pack(fill="both", expand=True, padx=12, pady=5)
        scroll = tk.Scrollbar(content)
        scroll.pack(side="right", fill="y")
        result_list = tk.Listbox(content, bg=PINK_LIGHT, fg=PINK_TEXT,
                                 selectbackground=PINK_ACCENT, selectforeground="white",
                                 font=("Consolas", 10), relief="flat",
                                 activestyle="none", yscrollcommand=scroll.set)
        result_list.pack(side="left", fill="both", expand=True)
        scroll.config(command=result_list.yview)
        for i, path in matches:
            result_list.insert("end", f"{i + 1:04d}  {path}")
        result_list.selection_set(0)
        result_list.activate(0)

        def open_selected(event=None):
            selection = result_list.curselection()
            if not selection:
                return
            target_idx = matches[selection[0]][0]
            if self.go_to_image(target_idx):
                dialog.destroy()

        result_list.bind("<Double-Button-1>", open_selected)
        result_list.bind("<Return>", open_selected)
        self.button(dialog, "🐾 Abrir imagem / Open image", open_selected,
                    strong=True).pack(pady=(5, 12))
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.grab_set()
        result_list.focus_set()

    def close(self):
        if self.confirm_change():
            self.root.destroy()


if __name__ == "__main__":
    print("VERSÃO CORRIGIDA: ATALHOS PRIORITÁRIOS + DIAGNÓSTICO VISUAL", flush=True)
    root = tk.Tk()
    EarAnnotator(root)
    root.mainloop()