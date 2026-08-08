import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.evaluator.phonetic_matcher import PhoneticMatcher
from src.database.progress_db import ProgressDatabase
from src.audio.tts_engine import TTSEngine
from src.audio.player import AudioPlayer

class TestCITrainerComponents(unittest.TestCase):

    def setUp(self):
        self.matcher = PhoneticMatcher()
        self.db = ProgressDatabase(db_path=":memory:")

    def test_phonetic_matcher_exact(self):
        res = self.matcher.evaluate("Pass", "Pass")
        self.assertTrue(res["is_correct"])
        self.assertEqual(res["score"], 100.0)

    def test_phonetic_matcher_partial(self):
        res = self.matcher.evaluate("Bass", "Pass")
        self.assertIn("Anlaut: 'P' statt 'B'", res["message"])
        self.assertTrue(res["score"] > 0)

    def test_database_logging(self):
        self.db.log_attempt("Minimalpaare", "P vs B", "Pass", "Pass", True, 100.0)
        self.db.log_attempt("Minimalpaare", "P vs B", "Bass", "Pass", False, 50.0)
        
        stats = self.db.get_stats()
        self.assertEqual(stats["total_attempts"], 2)
        self.assertEqual(stats["correct_attempts"], 1)
        self.assertEqual(stats["accuracy"], 50.0)

    def test_tts_engine_mac_fallback(self):
        tts = TTSEngine(cache_dir=".cache/test_audio")
        audio_file = tts.generate_audio("Hallo Test", rate=1.0)
        self.assertTrue(os.path.exists(audio_file))
        if os.path.exists(audio_file):
            os.remove(audio_file)

    def test_audio_player_noise_volume_config(self):
        player = AudioPlayer(noise_file="data/rauschen.mp3")
        player.sync_noise(mask_noise=True, balance=-1.0, noise_volume=0.65)
        self.assertIsNotNone(player.current_noise_config)
        self.assertEqual(player.current_noise_config[:3], ("masking", "right", 0.65))
        player.stop_noise()
    def test_audio_player_synchronous_play(self):
        player = AudioPlayer(noise_file="data/rauschen.mp3")
        tts = TTSEngine(cache_dir=".cache/test_audio")
        audio_file = tts.generate_audio("Test", rate=1.0)
        # Verify that play with wait_until_done=True completes without errors
        player.play(audio_file, mask_noise=False, wait_until_done=True)
        if os.path.exists(audio_file):
            os.remove(audio_file)

if __name__ == "__main__":
    unittest.main()
