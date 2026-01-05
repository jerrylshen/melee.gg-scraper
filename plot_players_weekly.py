import csv
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.ticker as ticker


def plot(game, filename):

    game_dict = {
        "StarWarsUnlimited": "SWU",
        "Lorcana": "LORCANA"
    }

    week_counts = Counter()
    weekly_players = defaultdict(set)  # key: week_start_date (YYYY-%m-%d), value: set of unique players

    with open(filename, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            date_str = row["DATE"]
            try:
                date = datetime.strptime(date_str.strip(), "%Y/%m/%d")

                # Only include 2024–current year
                if date.year < 2024 or date > datetime.today():
                    continue

                # Find the Monday of the week
                week_start = date - timedelta(days=date.weekday())
                week_key = week_start.strftime("%Y-%m-%d")

                week_counts[week_key] += 1

                player_id = row["PLAYER_NAME"].strip()
                weekly_players[week_key].add(player_id)

            except ValueError:
                continue

    # --- FILTER: only include data starting from Jan 2024 ---
    start_date = datetime(2024, 1, 1)

    week_counts = {
        k: v for k, v in week_counts.items()
        if datetime.strptime(k, "%Y-%m-%d") >= start_date
    }
    weekly_players = {
        k: v for k, v in weekly_players.items()
        if datetime.strptime(k, "%Y-%m-%d") >= start_date
    }

    # Create full weekly range
    if not week_counts:
        raise ValueError("No valid date data found.")

    min_week = min(datetime.strptime(w, "%Y-%m-%d") for w in week_counts)
    max_week = max(datetime.strptime(w, "%Y-%m-%d") for w in week_counts)

    # Align to full weeks (Monday)
    min_week = min_week - timedelta(days=min_week.weekday())
    max_week = max_week - timedelta(days=max_week.weekday())

    all_weeks = pd.date_range(start=min_week, end=max_week, freq="W-MON").strftime("%Y-%m-%d").tolist()

    # Fill counts
    total_counts = [week_counts.get(week, 0) for week in all_weeks]
    unique_counts = [len(weekly_players.get(week, set())) for week in all_weeks]

    # Plot
    plt.figure(figsize=(24, 12))
    plt.plot(all_weeks, total_counts, marker="o", label="Total Plays")
    plt.plot(all_weeks, unique_counts, marker="s", color="orange", label="Unique Players")

    plt.title(f"{game_dict[game]} Weekly Player Statistics (Monday-Sunday)", fontsize=12)
    plt.xlabel("Labels: Every 2nd Week", fontsize=10)
    plt.ylabel("Count", fontsize=10)

    plt.gca().yaxis.set_major_locator(ticker.MultipleLocator(1000))

    plt.xticks(rotation=60, fontsize=8)
    plt.yticks(fontsize=8)

    # top padding to prevent number overlap with edge
    y_min, y_max = plt.ylim()
    plt.ylim(y_min, y_max * 1.0)

    
    if len(all_weeks) > 30:
        plt.xticks(all_weeks[::2])  # show every 2nd week label

    # text labels with vertical offset
    for i, week in enumerate(all_weeks):
        if total_counts[i] > 0:
            plt.text(
                week, total_counts[i] + (y_max * 0.02), str(total_counts[i]),
                ha="center", va="bottom", fontsize=8, color="blue"
            )
        if unique_counts[i] > 0:
            plt.text(
                week, unique_counts[i] + (y_max * 0.02), str(unique_counts[i]),
                ha="center", va="bottom", fontsize=8, color="orange"
            )

    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    plt.savefig(f"{game}/{game_dict[game]}_weekly_players_20260101.png")
    plt.show()


game = "StarWarsUnlimited"
# game = "Lorcana"
players_filename = f"{game}/players.csv"
plot(game, players_filename)