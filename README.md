# KICKGENERATOR Code

import numpy as np
import sounddevice as sd
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

DEFAULT_FREQ = 60
DEFAULT_VOLUME = 0.5
DEFAULT_ENVELOPE = {'attack': 0.01, 'decay': 0.2, 'sustain': 0.7, 'release': 0.3}
DEFAULT_DECAY_TYPE = "Lineal"

class KickGenerator:
    def __init__(self):
        self.freq = DEFAULT_FREQ
        self.volume = DEFAULT_VOLUME
        self.envelope = DEFAULT_ENVELOPE.copy()
        self.sample_rate = 44100
        self.decay_type = DEFAULT_DECAY_TYPE

    def generate_kick(self):
        total_duration = (self.envelope['attack'] +
                          self.envelope['decay'] +
                          self.envelope['release'] + 1)

        t = np.linspace(0, total_duration, int(self.sample_rate * total_duration), endpoint=False)
        sine_wave = np.sin(2 * np.pi * self.freq * t)
        env = self.create_envelope(t)
        kick = sine_wave * env * self.volume
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

        self.add_slider_with_entry(self.main_frame, "Frecuencia (Hz)", 20, 200, self.update_kick, DEFAULT_FREQ)
        self.add_slider_with_entry(self.main_frame, "Volumen", 0, 1, self.update_kick, DEFAULT_VOLUME)

        self.play_button = ttk.Button(self.main_frame, text="Preescucha", command=self.play_kick)
        self.play_button.pack()

        self.attack_slider = self.add_slider_with_entry(self.envelope_frame, "Attack (s)", 0, 1, self.update_envelope, DEFAULT_ENVELOPE['attack'])
        self.decay_slider = self.add_slider_with_entry(self.envelope_frame, "Decay (s)", 0, 1, self.update_envelope, DEFAULT_ENVELOPE['decay'])
        self.sustain_slider = self.add_slider_with_entry(self.envelope_frame, "Sustain (0-1)", 0, 1, self.update_envelope, DEFAULT_ENVELOPE['sustain'])
        self.release_slider = self.add_slider_with_entry(self.envelope_frame, "Release (s)", 0, 1, self.update_envelope, DEFAULT_ENVELOPE['release'])

        ttk.Label(self.envelope_frame, text="Decay Type").pack(pady=5)
        self.decay_type = ttk.Combobox(self.envelope_frame, values=["Lineal", "Exponencial"], state="readonly")
        self.decay_type.set(DEFAULT_DECAY_TYPE)
        self.decay_type.bind("<<ComboboxSelected>>", lambda e: self.update_envelope())
        self.decay_type.pack()

        self.figure, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.main_frame)
        self.canvas.get_tk_widget().pack(expand=True, fill="both")

        self.update_kick()

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

        return slider  # Devuelve el slider para poder usarlo más adelante.

    def update_entry(self, entry, value):
        entry.delete(0, tk.END)
        entry.insert(0, f"{float(value):.2f}")

    def update_slider(self, slider, entry):
        try:
            value = float(entry.get())
            slider.set(value)
            self.update_envelope()  # Actualiza el sonido y el gráfico al cambiar el valor del entry
        except ValueError:
            pass

    def update_envelope(self, *args):
        self.kick_generator.envelope['attack'] = float(self.attack_slider.get())
        self.kick_generator.envelope['decay'] = float(self.decay_slider.get())
        self.kick_generator.envelope['sustain'] = float(self.sustain_slider.get())
        self.kick_generator.envelope['release'] = float(self.release_slider.get())
        self.kick_generator.decay_type = self.decay_type.get()
        self.update_kick()  # Asegura que el gráfico y el sonido se actualicen al cambiar el envelope

    def update_kick(self, *args):
        t, kick, env = self.kick_generator.generate_kick()

        self.ax.clear()
        self.ax.plot(t[:1000], kick[:1000], label="Forma de Onda", alpha=0.7)
        self.ax.plot(t[:1000], env[:1000], label="Envelope", alpha=0.7)
        self.ax.set_title("Kick y Envelope Superpuestos")
        self.ax.set_xlabel("Tiempo (s)")
        self.ax.set_ylabel("Amplitud")
        self.ax.legend()

        self.canvas.draw()

    def play_kick(self):
        _, kick, _ = self.kick_generator.generate_kick()
        sd.play(kick, samplerate=self.kick_generator.sample_rate)

if __name__ == "__main__":
    app = App()
    app.mainloop()
