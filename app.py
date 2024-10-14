import sounddevice as sd
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import scipy.io.wavfile as wav
import numpy as np
import kick_generator as KickGen
import settings
import time
import threading

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Kick Maker")
        self.geometry("800x600")
        self.kick_generator = KickGen.KickGenerator()
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.playing_continuously = False

    def on_closing(self):
        # Detén cualquier proceso activo (como el audio)
        sd.stop()  # Si tienes algo reproduciendo en sounddevice, lo detienes
        # Termina el loop de Tkinter y destruye la ventana
        self.quit()  # Finaliza el mainloop
        self.destroy()  # Destruye la ventana

    def create_widgets(self):
        # Creamos un frame general para contener el gráfico y las pestañas
        self.main_container = ttk.Frame(self)
        self.main_container.pack(expand=True, fill="both",)

        #botones en mainframe
        self.random_button = ttk.Button(self.main_container, text="Randomizar Parámetros", command=self.randomize_parameters)
        self.random_button.pack(side="bottom")

        self.export_button = ttk.Button(self.main_container, text="Exportar como WAV", command=self.export_kick)
        self.export_button.pack(side="bottom")

        self.play_button = ttk.Button(self.main_container, text="Preescucha", command=self.play_kick)
        self.play_button.pack(side="bottom")

        self.bpm_slider = self.add_slider_with_entry(self.main_container, "BPM", 1, 400, None, settings.DEFAULT_BPM)

        self.play_temp_button = ttk.Button(self.main_container, text="Reproducción continua", command=self.start_play_kick_cont)
        self.play_temp_button.pack(side="left")

        self.stop_temp_button = ttk.Button(self.main_container, text="Detener reproducción", command=self.stop_play_kick_cont)
        self.stop_temp_button.pack(side="left")

        # Creamos un frame exclusivo para el gráfico
        self.graph_frame = ttk.Frame(self.main_container)
        self.graph_frame.pack(side="bottom", fill="both", expand=True)

        # Creamos el Notebook para las pestañas
        self.notebook = ttk.Notebook(self.main_container)
        self.notebook.pack(side="top", expand=True, fill="both")

        # Creamos los frames para cada pestaña
        self.main_frame = ttk.Frame(self.notebook)
        self.envelope_frame = ttk.Frame(self.notebook)
        self.noise_frame = ttk.Frame(self.notebook)

        # Añadimos los frames al Notebook
        self.notebook.add(self.main_frame, text="Kick")
        self.notebook.add(self.envelope_frame, text="Envelope")
        self.notebook.add(self.noise_frame, text="Noise")

        # Añadimos widgets a las pestañas
        self.add_waveform_selector(self.main_frame)
        self.add_kick_controls(self.main_frame)  # Para sliders y botones de la pestaña "Kick"
        self.add_envelope_controls(self.envelope_frame)  # Para sliders y controles de la pestaña "Envelope"
        self.add_noise_controls(self.noise_frame)  # Para controles de la pestaña "Noise"

        # Dibujar el gráfico en el frame general
        self.draw_signal_kick(self.graph_frame)

    def add_kick_controls(self, frame):
        self.freq_slider = self.add_slider_with_entry(frame, "Frecuencia (Hz)", 20, 200, self.update_freq, settings.DEFAULT_FREQ)
        self.volume_slider = self.add_slider_with_entry(frame, "Volumen", 0, 1, self.update_volume, settings.DEFAULT_VOLUME)

    def add_envelope_controls(self, frame):
        self.attack_slider = self.add_slider_with_entry(frame, "Attack (s)", 0, 1, self.update_envelope, settings.DEFAULT_ENVELOPE['attack'])
        self.decay_slider = self.add_slider_with_entry(frame, "Decay (s)", 0, 1, self.update_envelope, settings.DEFAULT_ENVELOPE['decay'])
        self.sustain_slider = self.add_slider_with_entry(frame, "Sustain (0-1)", 0, 1, self.update_envelope, settings.DEFAULT_ENVELOPE['sustain'])
        self.release_slider = self.add_slider_with_entry(frame, "Release (s)", 0, 1, self.update_envelope, settings.DEFAULT_ENVELOPE['release'])

        ttk.Label(frame, text="Decay Type").pack(pady=5)
        self.decay_type = ttk.Combobox(frame, values=["Lineal", "Exponencial"], state="readonly")
        self.decay_type.set(settings.DEFAULT_DECAY_TYPE)
        self.decay_type.bind("<<ComboboxSelected>>", lambda e: self.update_envelope())
        self.decay_type.pack()

    def add_noise_controls(self, frame):
        ttk.Label(frame, text="Tipo de Filtro").place(x=15, y=40)
        self.noise_filter_type = ttk.Combobox(frame, values=["Filtro 1", "Filtro 2"], state="readonly")
        self.noise_filter_type.set(settings.DEFAULT_FILTER_TYPE)
        self.noise_filter_type.place(x=100, y=40)
        self.noise_filter_type.bind("<<ComboboxSelected>>", lambda e: self.update_noise())
        self.noise_volume_slider = self.add_slider_with_entry(frame, "Volumen", 0.0, 1.0, self.update_volume, settings.DEFAULT_VOLUME)


    def draw_signal_kick(self, frame):
        self.figure, self.ax = plt.subplots(figsize=(4, 2))
        self.canvas = FigureCanvasTkAgg(self.figure, master=frame)
        self.canvas.get_tk_widget().pack(expand=True, fill="both")
        self.update_kick()

    def add_waveform_selector(self, parent):
        waveform_label = ttk.Label(parent, text="Seleccionar Forma de Onda:")
        waveform_label.pack(pady=5)

        self.waveform_selector = ttk.Combobox(parent, values=["Senoidal", "Cuadrada", "Triangular", "Sierra"], state="readonly")
        self.waveform_selector.set(settings.DEFAULT_WAVEFORM)
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
            self.update_volume()
            self.update_freq()
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

    def start_play_kick_cont(self):
        if not self.playing_continuously:
            self.playing_continuously = True
            self.play_kick_cont()  # Llama a la función de reproducción continua

    def play_kick_cont(self):
        if self.playing_continuously:
            self.play_kick()  # Reproduce el kick
            # Reprograma la siguiente reproducción según los BPM
            bpm = self.bpm_slider.get()
            interval = 60 / float(bpm) * 1000  # Convertir a milisegundos
            self.after(int(interval), self.play_kick_cont)  # Reprograma

    def stop_play_kick_cont(self):
        self.playing_continuously = False  # Cambia el estado a False

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
