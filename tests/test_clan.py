import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Adiciona o diretório raiz ao path para os imports funcionarem
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.clan_verifier import verify_clan_entries
from utils.ai_helper import AIHelper

class TestClanVerification(unittest.IsolatedAsyncioTestCase):
    def test_verify_clan_entries_success(self):
        detected_data = {
            "total_encontrado": 3,
            "jogadores": [
                {"nome": "Player1", "data_hora": "06/23/26 18:10"},
                {"nome": "Player2", "data_hora": "06/23/26 19:20"},
                {"nome": "Player3", "data_hora": None}
            ]
        }
        res = verify_clan_entries(3, detected_data)
        self.assertTrue(res["coincide"])
        self.assertEqual(res["total_detectado"], 3)
        self.assertIn("coincide", res["status_text"].lower())
        self.assertEqual(res["status_color"], 0x2ecc71)

    def test_verify_clan_entries_divergence_less(self):
        detected_data = {
            "total_encontrado": 2,
            "jogadores": [
                {"nome": "Player1", "data_hora": "06/23/26 18:10"},
                {"nome": "Player2", "data_hora": "06/23/26 19:20"}
            ]
        }
        res = verify_clan_entries(4, detected_data)
        self.assertFalse(res["coincide"])
        self.assertEqual(res["total_detectado"], 2)
        self.assertIn("divergência", res["status_text"].lower())
        self.assertEqual(res["status_color"], 0xe74c3c)

    def test_verify_clan_entries_divergence_more(self):
        detected_data = {
            "total_encontrado": 4,
            "jogadores": [
                {"nome": "Player1", "data_hora": "06/23/26 18:10"},
                {"nome": "Player2", "data_hora": "06/23/26 19:20"},
                {"nome": "Player3", "data_hora": None},
                {"nome": "Player4", "data_hora": None}
            ]
        }
        res = verify_clan_entries(2, detected_data)
        self.assertFalse(res["coincide"])
        self.assertEqual(res["total_detectado"], 4)

    def test_verify_clan_entries_normalization(self):
        detected_data = {
            "total_encontrado": 10,
            "jogadores": [
                {"nome": "Player1", "data_hora": "06/23/26 18:10"},
                {"nome": "Player2", "data_hora": "06/23/26 19:20"}
            ]
        }
        res = verify_clan_entries(2, detected_data)
        self.assertTrue(res["coincide"])
        self.assertEqual(res["total_detectado"], 2)

    @patch("utils.ai_helper.genai.Client")
    async def test_analyze_clan_image_with_markdown_cleaning(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.text = """
        ```json
        {
          "total_encontrado": 2,
          "jogadores": [
             {"nome": "YonaSylusDepay", "data_hora": "06/23/26 22:56"},
             {"nome": "Yamada_Jones", "data_hora": "06/23/26 22:56"}
          ]
        }
        ```
        """
        mock_client.models.generate_content.return_value = mock_response

        with patch("utils.ai_helper.GOOGLE_API_KEY", "dummy_key"):
            helper = AIHelper()
            result = await helper.analyze_clan_image(b"dummy_bytes", "image/png")
            
            self.assertEqual(result["total_encontrado"], 2)
            self.assertEqual(len(result["jogadores"]), 2)
            self.assertEqual(result["jogadores"][0]["nome"], "YonaSylusDepay")
            self.assertEqual(result["jogadores"][1]["nome"], "Yamada_Jones")

if __name__ == "__main__":
    unittest.main()
