"""
utils/voice_helper.py — Gerenciamento de gravação, mixagem e exportação de áudio
=============================================================================
Implementa o acúmulo de pacotes de voz e a pós-processamento para gerar WAV mono 16kHz.
"""

import os
import time
import wave
import array
from typing import List, Tuple, Dict, Optional
import discord

# Como discord-ext-voice-recv é opcional/pode falhar no import se não instalado no ambiente
try:
    from discord.ext import voice_recv
    HAS_VOICE_RECV = True
except ImportError:
    HAS_VOICE_RECV = False
    # Mock simples para evitar erros de importação se usado fora do bot principal
    class voice_recv:
        class AudioSink:
            def __init__(self): pass

class VoiceRecorderSink(voice_recv.AudioSink):
    """
    Sink customizado para gravação de voz.
    Acumula pacotes PCM brutos (48000Hz, estéreo, 16-bit signed) na memória.
    """
    def __init__(self):
        super().__init__()
        self.packets: List[Tuple[str, int, float, bytes]] = [] # (username, user_id, timestamp, pcm_bytes)
        self.start_time: float = time.time()

    def wants_opus(self) -> bool:
        # Retorna False para receber pacotes PCM já decodificados pelo discord.py
        return False

    def write(self, user: Optional[discord.Member], data):
        # O parâmetro data é do tipo VoiceData da extensão voice_recv
        if not data.pcm:
            return
        
        user_name = user.display_name if user else "Desconhecido"
        user_id = user.id if user else 0
        timestamp = time.time()
        self.packets.append((user_name, user_id, timestamp, data.pcm))

    def cleanup(self):
        pass


def mix_and_downsample_packets(packets: List[Tuple[str, int, float, bytes]], start_time: float) -> bytes:
    """
    Mescla todos os pacotes de voz gravados em um único fluxo de áudio PCM mono a 16000Hz.
    Trata silêncio entre falas e sobreposições de falas simultâneas de forma segura.
    """
    if not packets:
        return b""

    # Ordena pacotes por timestamp para segurança
    sorted_packets = sorted(packets, key=lambda p: p[2])

    # Calcula a duração total estimada
    last_packet = sorted_packets[-1]
    last_packet_time = last_packet[2]
    last_packet_duration = len(last_packet[3]) / (48000 * 2 * 2) # 48000Hz, stereo, 16-bit = 4 bytes por frame
    duration = last_packet_time - start_time + last_packet_duration + 0.5
    
    # Prepara o array master no formato 16000Hz, Mono, 16-bit signed int
    total_samples = int(duration * 16000)
    master_samples = array.array('h', [0] * total_samples)

    for user_name, user_id, timestamp, pcm_bytes in sorted_packets:
        offset_seconds = timestamp - start_time
        if offset_seconds < 0:
            offset_seconds = 0
            
        target_offset_samples = int(offset_seconds * 16000)
        
        # Converte os bytes PCM estéreo de 48000Hz em array de 16-bit signed ints
        packet_samples = array.array('h', pcm_bytes)
        
        # Downsample de 48000Hz estéreo -> 16000Hz mono (decimação por 6)
        # Slicing: [0::6] pega o canal esquerdo (0) a cada 6 elementos (3 frames de tamanho 2 samples)
        packet_mono_16k = packet_samples[0::6]
        
        # Garante que o array principal seja estendido se o pacote ultrapassar o limite atual
        required_length = target_offset_samples + len(packet_mono_16k)
        if len(master_samples) < required_length:
            master_samples.extend([0] * (required_length - len(master_samples)))
            
        # Mixa os samples no buffer master
        for idx, sample in enumerate(packet_mono_16k):
            target_idx = target_offset_samples + idx
            val = master_samples[target_idx] + sample
            
            # Clamp de 16-bit assinado para evitar distorção de clipping digital
            if val > 32767:
                val = 32767
            elif val < -32768:
                val = -32768
            master_samples[target_idx] = val

    return master_samples.tobytes()


def extract_speaker_segments(packets: List[Tuple[str, int, float, bytes]], start_time: float, gap_threshold: float = 1.5) -> List[Dict]:
    """
    Agrupa pacotes individuais de voz por falante em turnos/frases contínuas.
    Retorna uma lista ordenada cronologicamente de segmentos contendo:
    - user: Nome do usuário
    - start: Segundo de início relativo
    - end: Segundo de fim relativo
    """
    if not packets:
        return []

    sorted_packets = sorted(packets, key=lambda p: p[2])
    raw_segments = []
    
    # Rastreia o último segmento ativo por user_id
    active_segments = {}

    for user_name, user_id, timestamp, pcm_bytes in sorted_packets:
        rel_time = timestamp - start_time
        duration = len(pcm_bytes) / (48000 * 2 * 2)
        rel_end_time = rel_time + duration

        if user_id in active_segments:
            last_seg = active_segments[user_id]
            # Se o tempo entre o fim do último pacote e o início deste for menor que o threshold, estende
            if rel_time - last_seg["end"] < gap_threshold:
                last_seg["end"] = rel_end_time
            else:
                # Fecha o segmento antigo, envia para a lista e inicia um novo
                raw_segments.append(last_seg.copy())
                last_seg["start"] = rel_time
                last_seg["end"] = rel_end_time
                last_seg["user"] = user_name
        else:
            active_segments[user_id] = {
                "user": user_name,
                "start": rel_time,
                "end": rel_end_time
            }

    # Adiciona os segmentos finais ainda ativos
    for seg in active_segments.values():
        raw_segments.append(seg)

    # Ordena todos os segmentos por tempo de início
    return sorted(raw_segments, key=lambda s: s["start"])


def save_mono_wav(pcm_bytes: bytes, filepath: str):
    """
    Salva dados PCM mono 16000Hz no formato de arquivo WAV padrão.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with wave.open(filepath, "wb") as wf:
        wf.setnchannels(1)     # Mono
        wf.setsampwidth(2)     # 16-bit PCM = 2 bytes
        wf.setframerate(16000) # 16000 Hz
        wf.writeframes(pcm_bytes)
