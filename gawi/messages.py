"""The friendly words of the app, in one place (no Flask, easy to test).

The rule: cheer people on, never make them feel guilty. A missed day
is just "Let's start", never "You failed".
"""

# Every emoji the app writes outside the habit icons (here, in flash
# messages and in templates), so the emoji font includes them (see create_app).
EMOJI = ["☀️", "🌤️", "🌙", "🌿", "🌱", "🌅", "💪", "🔥", "✨", "🎉"]


def greeting(hour):
    """A greeting for the time of day, in Filipino: (words, emoji)."""
    if 5 <= hour < 12:
        return "Magandang umaga", "☀️"
    if 12 <= hour < 18:
        return "Magandang hapon", "🌤️"
    return "Magandang gabi", "🌙"


def progress_message(done, total):
    """A short cheer for how far today has come."""
    left = total - done
    if total == 0:
        return "Nothing for today. Enjoy your rest! 🌿"
    if left == 0:
        return "Perfect day! Ang galing mo! 🌅"
    if done == 0:
        return "Let's start with one small step. 🌱"
    if left == 1:
        return "Just 1 more. Kaya mo 'yan! 💪"
    if done * 2 >= total:
        return f"Halfway there! {left} to go. 🔥"
    return f"Nice start! {left} to go. ✨"
