import sys
import os
import time
import array
import unittest
from unittest.mock import MagicMock, patch

# Adiciona o diretório raiz ao path para importar os módulos corretos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.voice_helper import (
    VoiceRecorderSink,
    mix_and_downsample_packets,
    extract_speaker_segments,
    save_mono_wav
)
from utils.ai_helper import AIHelper

class TestVoiceSystem(unittest.IsolatedAsyncioTestCase):
    """
    Testes unitários para validar a lógica de captura, downsampling,
    mixagem de múltiplos usuários e transcrição de áudio.
    """

    def setUp(self):
        self.start_time = time.time()

    def test_downsampling_decimation(self):
        """
        Verifica se a decimação por 6 (48000Hz estéreo -> 16000Hz mono)
        seleciona corretamente apenas o canal esquerdo de cada 3º frame.
        """
        # Cria 12 frames de áudio estéreo 16-bit (24 samples no total)
        # Cada sample L = i * 10, cada sample R = i * 10 + 5
        samples = []
        for i in range(12):
            samples.extend([i * 10, i * 10 + 5])
            
        pcm_bytes = array.array('h', samples).tobytes()
        packets = [
            ("User A", 123, self.start_time, pcm_bytes)
        ]
        
        mixed_pcm = mix_and_downsample_packets(packets, self.start_time)
        result_samples = array.array('h', mixed_pcm)
        
        # Esperado: samples da esquerda a cada 3 frames (i.e. i=0, i=3, i=6, i=9)
        # L0 = 0, L3 = 30, L6 = 60, L9 = 90
        self.assertEqual(len(result_samples), 4)
        self.assertEqual(list(result_samples), [0, 30, 60, 90])

    def test_audio_mixing_clamping(self):
        """
        Verifica se a mixagem de múltiplos usuários sobrepostos soma as vozes
        e realiza o clamp nos limites de 16-bit assinado (-32768 a 32767).
        """
        # Pacote do User A em t=0s
        # Pcm com 6 frames estéreo (12 samples) contendo valor 20000
        samples_a = [20000] * 12
        bytes_a = array.array('h', samples_a).tobytes()
        
        # Pacote do User B em t=0s (totalmente sobreposto)
        # Pcm com 6 frames estéreo contendo valor 15000
        samples_b = [15000] * 12
        bytes_b = array.array('h', samples_b).tobytes()
        
        packets = [
            ("User A", 1, self.start_time, bytes_a),
            ("User B", 2, self.start_time, bytes_b)
        ]
        
        mixed_pcm = mix_and_downsample_packets(packets, self.start_time)
        result_samples = array.array('h', mixed_pcm)
        
        # Cada pacote de 6 frames estéreo vira 2 samples mono
        self.assertEqual(len(result_samples), 2)
        # A soma seria 20000 + 15000 = 35000, que excede 32767. Deve ser clampado para 32767.
        self.assertEqual(list(result_samples), [32767, 32767])

    def test_speaker_segmentation_diarization(self):
        """
        Valida o agrupamento de pacotes de fala. Pacotes do mesmo usuário
        com pouca diferença devem se fundir, e com grande diferença criar novos segmentos.
        """
        # Duração de cada pacote = 0.02s
        duration = 0.02
        pcm_bytes = b'\x00' * 384 # 20ms de áudio estéreo 48k
        
        packets = [
            # Fala 1 do User A (t=1.00s e t=1.02s) - devem se fundir
            ("User A", 100, self.start_time + 1.00, pcm_bytes),
            ("User A", 100, self.start_time + 1.02, pcm_bytes),
            
            # Fala do User B (t=2.00s)
            ("User B", 200, self.start_time + 2.00, pcm_bytes),
            
            # Fala 2 do User A (t=5.00s) - após o threshold de 1.5s, deve criar um novo segmento
            ("User A", 100, self.start_time + 5.00, pcm_bytes),
        ]
        
        segments = extract_speaker_segments(packets, self.start_time, gap_threshold=1.5)
        
        # Esperado 3 segmentos no total, ordenados por start time
        self.assertEqual(len(segments), 3)
        
        # Segmento 1: User A das proximidades de t=1.0 até t=1.04
        self.assertEqual(segments[0]["user"], "User A")
        self.assertAlmostEqual(segments[0]["start"], 1.0, places=2)
        self.assertAlmostEqual(segments[0]["end"], 1.04, places=2)
        
        # Segmento 2: User B das proximidades de t=2.0 até t=2.02
        self.assertEqual(segments[1]["user"], "User B")
        self.assertAlmostEqual(segments[1]["start"], 2.0, places=2)
        self.assertAlmostEqual(segments[1]["end"], 2.02, places=2)
        
        # Segmento 3: User A das proximidades de t=5.0 até t=5.02
        self.assertEqual(segments[2]["user"], "User A")
        self.assertAlmostEqual(segments[2]["start"], 5.0, places=2)
        self.assertAlmostEqual(segments[2]["end"], 5.02, places=2)

    @patch('utils.ai_helper.genai.Client')
    async def test_transcription_helper(self, mock_client_class):
        """
        Testa o método transcribe_audio no AIHelper com mock da chamada do Gemini.
        """
        # Configura o mock do cliente Gemini
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = "Jogador 1: Olá\nJogador 2: Como vai?"
        mock_client.models.generate_content.return_value = mock_response
        
        # Instancia helper
        ai_helper = AIHelper()
        
        # Cria arquivo temporário falso para teste
        filepath = "dummy_test_audio.wav"
        with open(filepath, "wb") as f:
            f.write(b"RIFF....WAVEfmt ....data....")
            
        try:
            segments = [{"user": "User A", "start": 0.0, "end": 1.0}]
            res = await ai_helper.transcribe_audio(filepath, segments)
            
            self.assertEqual(res, "Jogador 1: Olá\nJogador 2: Como vai?")
            mock_client.models.generate_content.assert_called_once()
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)


if __name__ == "__main__":
    unittest.main()
