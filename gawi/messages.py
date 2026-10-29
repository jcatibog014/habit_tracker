"""The friendly words of the app, in one place (no Flask, easy to test).

The rule: cheer people on, never make them feel guilty. A missed day
is just "a new start", never "you failed".
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


def progress_message(done, total, best_week=False):
    """A short cheer for how far today has come."""
    left = total - done
    if total == 0:
        message = "Nothing for today. Enjoy your rest! 🌿"
    elif left == 0:
        message = "Perfect day! Ang galing mo! 🌅"
    elif done == 0:
        message = "Let's start with one small step. 🌱"
    elif left == 1:
        message = "Just 1 more. Kaya mo 'yan! 💪"
    elif done * 2 >= total:
        message = f"Halfway there! {left} to go. 🔥"
    else:
        message = f"Nice start! {left} to go. ✨"
    if best_week:
        message += " Best week ever!"
    return message


def streak_label(count, unit):
    """12, "days" -> "12-day streak"."""
    return f"{count}-{unit[:-1]} streak"


def nudge(streak, longest, unit, done):
    """A gentle push on a habit that isn't done yet, or None.

    A streak of 3 or more is worth protecting; after a break we talk about
    a new start, never about what was lost.
    """
    if done:
        return None
    if streak >= 3:
        return f"{streak_label(streak, unit)}. Keep it going!"
    if streak == 0 and longest > 0:
        return "New start: day 1 today" if unit == "days" else "New start: week 1 this week"
    return None


def milestone_message(habit_name, count, unit):
    """The celebration when a streak reaches a badge."""
    return f"{count} {unit} of {habit_name}. Ang galing!"


# ---------- Quote of the day ----------

# (quote, who said it). Filipino salawikain, old sayings from around the
# world (long out of copyright), and a few lines of our own. Keep them short.
QUOTES = [
    ("Kapag may tiyaga, may nilaga.", "Salawikain"),
    ("Walang mahirap na gawa kapag dinaan sa tiyaga.", "Salawikain"),
    ("Daig ng maagap ang masipag.", "Salawikain"),
    ("Nasa Diyos ang awa, nasa tao ang gawa.", "Salawikain"),
    ("Kung ano ang itinanim, siya ring aanihin.", "Salawikain"),
    ("Pag may isinuksok, may madudukot.", "Salawikain"),
    ("Huli man daw at magaling, naihahabol din.", "Salawikain"),
    ("Pagkahaba-haba man ng prusisyon, sa simbahan din ang tuloy.", "Salawikain"),
    ("Ang lumalakad nang matulin, kung matinik ay malalim.", "Salawikain"),
    ("Habang maikli ang kumot, matutong mamaluktot.", "Salawikain"),
    ("Aanhin pa ang damo kung patay na ang kabayo?", "Salawikain"),
    ("The journey of a thousand miles begins with a single step.", "Lao Tzu"),
    ("Well done is better than well said.", "Benjamin Franklin"),
    ("Little strokes fell great oaks.", "Benjamin Franklin"),
    ("Lost time is never found again.", "Benjamin Franklin"),
    ("Diligence is the mother of good luck.", "Benjamin Franklin"),
    ("One today is worth two tomorrows.", "Benjamin Franklin"),
    ("He that can have patience can have what he will.", "Benjamin Franklin"),
    ("While we are postponing, life speeds by.", "Seneca"),
    ("We suffer more often in imagination than in reality.", "Seneca"),
    ("First say to yourself what you would be; and then do what you have to do.", "Epictetus"),
    ("No man is free who is not master of himself.", "Epictetus"),
    ("Waste no more time arguing what a good man should be. Be one.", "Marcus Aurelius"),
    ("Our life is what our thoughts make it.", "Marcus Aurelius"),
    ("Well begun is half done.", "Aristotle"),
    ("He who has begun is half done. Dare to be wise.", "Horace"),
    ("Practice is everything.", "Periander"),
    ("Knowing is not enough; we must apply.", "Goethe"),
    ("Great things are done by a series of small things brought together.", "Vincent van Gogh"),
    ("What we hope ever to do with ease, we must first learn to do with diligence.", "Samuel Johnson"),
    ("Act well your part; there all the honour lies.", "Alexander Pope"),
    ("Slow and steady wins the race.", "Aesop"),
    ("Fall seven times, stand up eight.", "Japanese proverb"),
    ("The best time to plant a tree was 20 years ago. The second best time is now.", "Chinese proverb"),
    ("A habit is first a cobweb, then a cable.", "Spanish proverb"),
    ("Little by little, one goes far.", "Spanish proverb"),
    ("Rome wasn't built in a day.", "Proverb"),
    ("Habit is second nature.", "Proverb"),
    ("Drop by drop, the pot is filled.", "Proverb"),
    ("Every day is a new beginning.", "Proverb"),
    ("Small steps every day beat big steps once in a while.", "Gawi"),
    ("You don't have to be perfect. You just have to show up.", "Gawi"),
    ("A missed day is a pause, not the end. Start again today.", "Gawi"),
    ("Today's tiny habit is tomorrow's big change.", "Gawi"),
    ("Every sunrise is a new chance to begin.", "Gawi"),
    ("Be proud of the small wins. They add up.", "Gawi"),
    ("Rest when you need to. Just don't quit.", "Gawi"),
    ("The best streak starts with day one.", "Gawi"),
    ("Do it for the you of next year.", "Gawi"),
    ("One small tick today, one big change someday.", "Gawi"),
    ("Kaya mo 'yan. One small step today.", "Gawi"),
    ("Hindi kailangang mabilis. Ang mahalaga, tuloy-tuloy.", "Gawi"),
]


def quote_of_the_day(day):
    """Today's quote: (index, quote, author). The same all day, a new one each morning."""
    index = day.toordinal() % len(QUOTES)
    quote, author = QUOTES[index]
    return index, quote, author
