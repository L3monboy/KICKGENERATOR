import numpy as np
import sounddevice as sd
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import scipy.io.wavfile as wav

DEFAULT_FREQ = 60
DEFAULT_VOLUME = 0.5
DEFAULT_ENVELOPE = {'attack': 0.01, 'decay': 0.2, 'sustain': 0.7, 'release': 0.3}
DEFAULT_DECAY_TYPE = "Lineal"
DEFAULT_WAVEFORM = "Senoidal"

class KickGenerator:
    def __init__(self):
        self.freq = DEFAULT_FREQ
        self.volume = DEFAULT_VOLUME
        self.envelope = DEFAULT_ENVELOPE.copy()
        self.sample_rate = 44100
        self.decay_type = DEFAULT_DECAY_TYPE
        self.waveform = DEFAULT_WAVEFORM

    def generate_kick(self):
        total_duration = (self.envelope['attack'] +
                          self.envelope['decay'] +
                          self.envelope['release'] + 1)

        t = np.linspace(0, total_duration, int(self.sample_rate * total_duration), endpoint=False)
        if self.waveform == "Senoidal":
            wave = np.sin(2 * np.pi * self.freq * t)
        elif self.waveform == "Cuadrada":
            wave = np.sign(np.sin(2 * np.pi * self.freq * t))
        elif self.waveform == "Triangular":
            wave = 2 * np.abs(2 * (t * self.freq - np.floor(1/2 + t * self.freq))) - 1
        elif self.waveform == "Sierra":
            wave = 2 * (t * self.freq - np.floor(t * self.freq + 0.5))
        
        env = self.create_envelope(t)
        kick = wave * env * self.volume
        return t, kick, env

    def create_envelope(self, t):
        total_samples = len(t)
        attack_samples = int(self.envelope['attack'] * self.sample_rate)
        decay_samples = int(self.envelope['decay'] * self.sample_rate)
        release_samples = int(self.envelope['release'] * self.sample_rate)
        sustain_samples = max(0, total_samples - attack_samples - decay_samples - release_samples)

        attack = np.linspace(0, 1, attack_samples, endpoint=False)
        if self.decay_type == "Lineal":
            decay = np.linspace(1, self.envelope['sustain'], decay_samples, endpoint=False)
        else:
            decay = np.exp(-np.linspace(0, 5, decay_samples)) * (1 - self.envelope['sustain']) + self.envelope['sustain']

        sustain = np.full(sustain_samples, self.envelope['sustain'])
        release = np.linspace(self.envelope['sustain'], 0, release_samples)

        envelope = np.concatenate([attack, decay, sustain, release])
        return envelope[:total_samples]

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Kick Maker")
        self.geometry("800x600")
        self.kick_generator = KickGenerator()
        self.create_widgets()

    def create_widgets(self):
        self.notebook = ttk.Notebook(self)
        self.main_frame = ttk.Frame(self.notebook)
        self.envelope_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.main_frame, text="Kick")
        self.notebook.add(self.envelope_frame, text="Envelope")
        self.notebook.pack(expand=True, fill="both")

        self.add_waveform_selector(self.main_frame)

        self.freq_slider = self.add_slider_with_entry(self.main_frame, "Frecuencia (Hz)", 20, 200, self.update_freq, DEFAULT_FREQ)
        self.volume_slider = self.add_slider_with_entry(self.main_frame, "Volumen", 0, 1, self.update_volume, DEFAULT_VOLUME)

        self.play_button = ttk.Button(self.main_frame, text="Preescucha", command=self.play_kick)
        self.play_button.pack()

        self.export_button = ttk.Button(self.main_frame, text="Exportar como WAV", command=self.export_kick)
        self.export_button.pack(pady=5)

        self.attack_slider = self.add_slider_with_entry(self.envelope_frame, "Attack (s)", 0, 1, self.update_envelope, DEFAULT_ENVELOPE['attack'])
        self.decay_slider = self.add_slider_with_entry(self.envelope_frame, "Decay (s)", 0, 1, self.update_envelope, DEFAULT_ENVELOPE['decay'])
        self.sustain_slider = self.add_slider_with_entry(self.envelope_frame, "Sustain (0-1)", 0, 1, self.update_envelope, DEFAULT_ENVELOPE['sustain'])
        self.release_slider = self.add_slider_with_entry(self.envelope_frame, "Release (s)", 0, 1, self.update_envelope, DEFAULT_ENVELOPE['release'])

        ttk.Label(self.envelope_frame, text="Decay Type").pack(pady=5)
        self.decay_type = ttk.Combobox(self.envelope_frame, values=["Lineal", "Exponencial"], state="readonly")
        self.decay_type.set(DEFAULT_DECAY_TYPE)
        self.decay_type.bind("<<ComboboxSelected>>", lambda e: self.update_envelope())
        self.decay_type.pack()

        self.random_button = ttk.Button(self.main_frame, text="Randomizar Parámetros", command=self.randomize_parameters)
        self.random_button.pack()

        self.figure, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.main_frame)
        self.canvas.get_tk_widget().pack(expand=True, fill="both")

        self.update_kick()  # Actualizar inicial

    def add_waveform_selector(self, parent):
        waveform_label = ttk.Label(parent, text="Seleccionar Forma de Onda:")
        waveform_label.pack(pady=5)

        self.waveform_selector = ttk.Combobox(parent, values=["Senoidal", "Cuadrada", "Triangular", "Sierra"], state="readonly")
        self.waveform_selector.set(DEFAULT_WAVEFORM)
        self.waveform_selector.bind("<<ComboboxSelected>>", self.update_waveform)
        self.waveform_selector.pack(pady=5)

        # Dibujo ilustrativo
        self.waveform_canvas = tk.Canvas(parent, width=300, height=100)
        self.waveform_canvas.pack(pady=5)
        self.draw_waveform()

    def draw_waveform(self):
        self.waveform_canvas.delete("all")
        width = 300
        height = 100
        waveform = self.waveform_selector.get()
        t = np.linspace(0, 1, 1000)

        if waveform == "Senoidal":
            wave = np.sin(2 * np.pi * t)
        elif waveform == "Cuadrada":
            wave = np.sign(np.sin(2 * np.pi * t))
        elif waveform == "Triangular":
            wave = 2 * np.abs(2 * (t - np.floor(t + 0.5))) - 1
        elif waveform == "Sierra":
            wave = 2 * (t - np.floor(t + 0.5))

        for i in range(len(wave) - 1):
            x0 = i * (width / len(wave))
            y0 = height / 2 * (1 - wave[i])
            x1 = (i + 1) * (width / len(wave))
            y1 = height / 2 * (1 - wave[i + 1])
            self.waveform_canvas.create_line(x0, y0, x1, y1, fill="black")

    def add_slider_with_entry(self, parent, label_text, min_val, max_val, command, default):
        frame = ttk.Frame(parent)
        frame.pack(pady=5, padx=10, anchor="w")

        ttk.Label(frame, text=label_text).pack(side="left", padx=5)

        slider = ttk.Scale(frame, from_=min_val, to=max_val, command=lambda v: self.update_entry(entry, v))
        slider.set(default)
        slider.pack(side="left", fill="x", expand=True, padx=5)

        entry = ttk.Entry(frame, width=5)
        entry.insert(0, str(default))
        entry.pack(side="left", padx=5)
        entry.bind("<Return>", lambda e: self.update_slider(slider, entry))

        slider.bind("<Motion>", lambda e: self.update_slider(slider, entry))

        return slider

    def update_entry(self, entry, value):
        entry.delete(0, tk.END)
        entry.insert(0, f"{float(value):.2f}")

    def update_slider(self, slider, entry):
        try:
            value = float(entry.get())
            slider.set(value)
            self.update_envelope()  # Actualiza sonido y gráfico cuando el campo de entrada cambia
        except ValueError:
            pass

    def update_waveform(self, *args):
        self.kick_generator.waveform = self.waveform_selector.get()
        self.draw_waveform()  # Actualiza la representación visual de la forma de onda
        self.update_kick()  # Asegúrate de que el gráfico y el sonido se actualicen

    def update_freq(self, *args):
        self.kick_generator.freq = float(self.freq_slider.get())
        self.update_kick()

    def update_volume(self, *args):
        self.kick_generator.volume = float(self.volume_slider.get())
        self.update_kick()

    def update_envelope(self, *args):
        self.kick_generator.envelope = {
            'attack': float(self.attack_slider.get()),
            'decay': float(self.decay_slider.get()),
            'sustain': float(self.sustain_slider.get()),
            'release': float(self.release_slider.get())
        }
        self.kick_generator.decay_type = self.decay_type.get()
        self.update_kick()

    def update_kick(self):
        t, kick, env = self.kick_generator.generate_kick()
        self.ax.clear()
        self.ax.plot(t, kick, label='Kick', color='blue')
        self.ax.plot(t, env, label='Envelope', color='orange', linestyle='--')
        self.ax.set_title("Waveform and Envelope")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Amplitude")
        self.ax.legend()
        self.canvas.draw()

    def play_kick(self):
        t, kick, _ = self.kick_generator.generate_kick()
        sd.play(kick, self.kick_generator.sample_rate)

    def export_kick(self):
        t, kick, _ = self.kick_generator.generate_kick()
        kick_to_export = (kick * 32767).astype(np.int16)  # Normalizar a 16-bit
        file_path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV files", "*.wav")])
        if file_path:
            wav.write(file_path, self.kick_generator.sample_rate, kick_to_export)

    def randomize_parameters(self):
        self.freq_slider.set(np.random.uniform(20, 200))
        self.volume_slider.set(np.random.uniform(0, 1))
        self.attack_slider.set(np.random.uniform(0, 1))
        self.decay_slider.set(np.random.uniform(0, 1))
        self.sustain_slider.set(np.random.uniform(0, 1))
        self.release_slider.set(np.random.uniform(0, 1))
        self.decay_type.set(np.random.choice(["Lineal", "Exponencial"]))
        self.update_envelope()

if __name__ == "__main__":
    app = App()
    app.mainloop()
