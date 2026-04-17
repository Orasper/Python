"""Regression tests for the ahorcado (hangman) game.

These tests invoke the game as a subprocess so they work against the
original script ("ahorcado game Python") without having to import it
(the file name contains spaces and has no .py extension, and the
module-level code starts the game immediately on import).
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GAME_SCRIPT = REPO_ROOT / "ahorcado game Python"

# The game's word list is: ["panadero", "dinosaurio", "Helipuerto", "Tiburon"].
# Together these words contain (case-insensitively) the letters:
#   a, b, d, e, h, i, l, n, o, p, r, s, t, u
# The letters below are guaranteed to be wrong no matter which palabra
# is randomly chosen, so feeding them one-by-one deterministically
# exhausts the six available attempts.
SAFE_WRONG_LETTERS = ["c", "f", "g", "j", "k", "m"]

LOSS_MESSAGE = "Te has quedado sin vidas"
PROMPT = "Elige una letra:"


def _run_game(letters: list[str], timeout: float = 10.0) -> subprocess.CompletedProcess[str]:
    """Run the ahorcado script, piping ``letters`` (one per line) to stdin."""
    stdin_payload = "\n".join(letters) + "\n"
    return subprocess.run(
        [sys.executable, str(GAME_SCRIPT)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class AhorcadoEndOfAttemptsRegressionTest(unittest.TestCase):
    """The game must end cleanly once the player runs out of attempts."""

    def test_game_script_exists(self) -> None:
        self.assertTrue(
            GAME_SCRIPT.is_file(),
            f"Expected to find the ahorcado script at {GAME_SCRIPT}",
        )

    def test_game_ends_after_six_wrong_guesses(self) -> None:
        """Feeding six wrong letters must trigger the loss branch and
        make the main loop exit without requesting more input."""
        result = _run_game(SAFE_WRONG_LETTERS)

        self.assertEqual(
            result.returncode,
            0,
            msg=(
                "Game exited with a non-zero status when attempts ran out.\n"
                f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            ),
        )
        self.assertIn(
            LOSS_MESSAGE,
            result.stdout,
            msg=(
                "Expected the loss message to be printed when attempts ran "
                f"out, got:\n{result.stdout}"
            ),
        )

    def test_game_stops_prompting_after_attempts_exhausted(self) -> None:
        """After six wrong guesses, the game must not ask for a seventh letter.

        We send seven letters; only six should be consumed before the game
        terminates, so the prompt must appear exactly six times.
        """
        extra_letter = "z"  # also never in any palabra
        result = _run_game(SAFE_WRONG_LETTERS + [extra_letter])

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        prompt_count = result.stdout.count(PROMPT)
        self.assertEqual(
            prompt_count,
            len(SAFE_WRONG_LETTERS),
            msg=(
                f"Game should have prompted exactly {len(SAFE_WRONG_LETTERS)} "
                f"times before ending, but prompted {prompt_count} times.\n"
                f"STDOUT:\n{result.stdout}"
            ),
        )

    def test_lives_counter_reaches_zero_before_loss(self) -> None:
        """The on-screen lives counter must decrement down to 1 before the
        game announces the loss (it starts at 6 and drops by one per wrong
        guess)."""
        result = _run_game(SAFE_WRONG_LETTERS)

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        for remaining in range(6, 0, -1):
            self.assertIn(
                f"vidas: {remaining}",
                result.stdout,
                msg=(
                    f"Expected to see 'vidas: {remaining}' in the output "
                    f"before the loss message.\nSTDOUT:\n{result.stdout}"
                ),
            )
        # The loss branch must fire only after the sixth wrong guess, so the
        # counter should never have been displayed as 0 (the loop exits first).
        self.assertNotIn("vidas: 0", result.stdout)
        self.assertLess(
            result.stdout.index(LOSS_MESSAGE),
            len(result.stdout),
            msg="Loss message was not printed.",
        )


if __name__ == "__main__":
    unittest.main()
