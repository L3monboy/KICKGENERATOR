import numpy as np
import settings




class KickGenerator:
    def __init__(self):
        self.freq = settings.DEFAULT_FREQ
        self.volume = settings.DEFAULT_VOLUME
        self.envelope = settings.DEFAULT_ENVELOPE.copy()
        self.sample_rate = 44100
        self.decay_type = settings.DEFAULT_DECAY_TYPE
        self.waveform = settings.DEFAULT_WAVEFORM
        self.duration = 5
        self.noise = np.random.normal(0, 1, self.duration * self.sample_rate)


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

    def create_noise(self):
        noise = np.random.normal(0, 1, self.duration * self.sample_rate)
        return noise

