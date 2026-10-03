import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from utils.music_helper import (
    get_ytdl_options,
    extract_song_info,
    search_songs,
    get_yt_suggestions,
)


class TestMusicHelper(unittest.IsolatedAsyncioTestCase):
    """
    Suíte de testes unitários para utils.music_helper.
    Estrutura: Arrange - Act - Assert (AAA).
    """

    def test_get_ytdl_options_default_and_custom(self):
        """Valida geração de opções com clientes móveis e verificação de cookies."""
        # Arrange & Act
        opts_default = get_ytdl_options()

        # Assert
        self.assertIn("extractor_args", opts_default)
        self.assertIn("youtube", opts_default["extractor_args"])
        self.assertIn("android", opts_default["extractor_args"]["youtube"]["player_client"])

        # Arrange: custom non-existent cookie file
        non_existent = Path("/tmp/non_existent_cookie_12345.txt")
        # Act
        opts_custom = get_ytdl_options(custom_cookies=non_existent)
        # Assert
        self.assertNotIn("cookiefile", opts_custom)

    async def test_extract_song_info_happy_path(self):
        """Caminho feliz: extração de áudio bem-sucedida do YouTube."""
        # Arrange
        mock_info = {
            "url": "https://stream.example.com/audio.mp3",
            "title": "Musica Teste",
            "thumbnail": "https://img.example.com/thumb.jpg",
            "webpage_url": "https://youtube.com/watch?v=123",
            "duration": 180,
        }

        with patch("yt_dlp.YoutubeDL") as MockYDL:
            ydl_instance = MockYDL.return_value.__enter__.return_value
            ydl_instance.extract_info.return_value = mock_info

            # Act
            result = await extract_song_info("https://youtube.com/watch?v=123")

            # Assert
            self.assertIsNotNone(result)
            self.assertEqual(result["title"], "Musica Teste")
            self.assertEqual(result["source"], "https://stream.example.com/audio.mp3")
            self.assertEqual(result["duration"], 180)

    async def test_extract_song_info_empty_or_none_query(self):
        """Caso de borda: query vazia ou nula."""
        # Act & Assert
        self.assertIsNone(await extract_song_info(""))
        self.assertIsNone(await extract_song_info(None))

    async def test_extract_song_info_youtube_fails_fallback_to_soundcloud(self):
        """Tratamento de exceções: YouTube falha e faz fallback para SoundCloud."""
        # Arrange
        mock_sc_entry = {
            "url": "https://soundcloud.example.com/audio.mp3",
            "title": "Musica SC",
            "thumbnail": "",
            "webpage_url": "https://soundcloud.com/123",
            "duration": 200,
        }

        def mock_extract(query, download=False):
            if "scsearch" in query:
                return {"entries": [mock_sc_entry]}
            raise RuntimeError("Sign in to confirm you're not a bot")

        with patch("yt_dlp.YoutubeDL") as MockYDL:
            ydl_instance = MockYDL.return_value.__enter__.return_value
            ydl_instance.extract_info.side_effect = mock_extract

            # Act
            result = await extract_song_info("musica legal")

            # Assert
            self.assertIsNotNone(result)
            self.assertIn("Musica SC", result["title"])
            self.assertEqual(result["source"], "https://soundcloud.example.com/audio.mp3")

    async def test_search_songs_happy_path(self):
        """Caminho feliz: busca de termos retornando múltiplos resultados."""
        # Arrange
        mock_entries = [
            {
                "url": f"https://stream.example.com/{i}.mp3",
                "title": f"Faixa {i}",
                "thumbnail": "",
                "webpage_url": f"https://yt.com/watch?v={i}",
                "duration": 100 + i,
            }
            for i in range(1, 4)
        ]

        with patch("yt_dlp.YoutubeDL") as MockYDL:
            ydl_instance = MockYDL.return_value.__enter__.return_value
            ydl_instance.extract_info.return_value = {"entries": mock_entries}

            # Act
            results = await search_songs("teste", limit=3)

            # Assert
            self.assertEqual(len(results), 3)
            self.assertEqual(results[0]["title"], "Faixa 1")

    async def test_search_songs_empty_query(self):
        """Caso de borda: query vazia."""
        # Act & Assert
        self.assertEqual(await search_songs(""), [])

    async def test_search_songs_youtube_blocked_falls_back_to_soundcloud(self):
        """Tratamento de erro: YouTube falha e fallback preenche os resultados via SoundCloud."""
        # Arrange
        mock_sc_entries = [
            {
                "url": "https://sc.example.com/song.mp3",
                "title": "SoundCloud Track",
                "thumbnail": "",
                "webpage_url": "https://soundcloud.com/song",
                "duration": 210,
            }
        ]

        def mock_extract(query, download=False):
            if "scsearch" in query:
                return {"entries": mock_sc_entries}
            raise RuntimeError("Bot block HTTP 429")

        with patch("yt_dlp.YoutubeDL") as MockYDL:
            ydl_instance = MockYDL.return_value.__enter__.return_value
            ydl_instance.extract_info.side_effect = mock_extract

            # Act
            results = await search_songs("alguma musica", limit=1)

            # Assert
            self.assertEqual(len(results), 1)
            self.assertIn("SoundCloud Track", results[0]["title"])
            self.assertEqual(results[0]["source"], "https://sc.example.com/song.mp3")

    async def test_get_yt_suggestions_empty(self):
        """Caso de borda: query vazia para sugestões."""
        # Act & Assert
        self.assertEqual(await get_yt_suggestions(""), [])


if __name__ == "__main__":
    unittest.main()
