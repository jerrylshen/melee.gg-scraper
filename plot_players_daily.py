import csv
from collections import Counter, defaultdict
from datetime import datetime, date
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.ticker as ticker


def plot(filename):

    game_dict = {
        "StarWarsUnlimited": "SWU",
        "Lorcana": "LORCANA"
    }
        
    day_counts = Counter()
    daily_players = defaultdict(set)

    with open(filename, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            date_str = row["DATE"]
            try:
                date = datetime.strptime(date_str.strip(), "%Y/%m/%d")
                # Only include 2024–current year
                if date < datetime(2024, 1, 1) or date > datetime.today():
                    continue

                day_key = date.strftime("%Y-%m-%d")

                day_counts[day_key] += 1

                player_id = row["PLAYER_NAME"].strip()
                daily_players[day_key].add(player_id)

            except ValueError:
                continue

    # --- FILTER: only include data starting from Jan 2024 ---
    start_date = datetime(2024, 1, 1)

    day_counts = {
        k: v for k, v in day_counts.items()
        if datetime.strptime(k, "%Y-%m-%d") >= start_date
    }
    daily_players = {
        k: v for k, v in daily_players.items()
        if datetime.strptime(k, "%Y-%m-%d") >= start_date
    }

    # Create full daily range
    if not day_counts:
        raise ValueError("No valid date data found.")

    min_day = min(datetime.strptime(d, "%Y-%m-%d") for d in day_counts)
    max_day = max(datetime.strptime(d, "%Y-%m-%d") for d in day_counts)

    all_days = pd.date_range(start=min_day, end=max_day, freq="D").strftime("%Y-%m-%d").tolist()

    # Fill counts
    total_counts = [day_counts.get(day, 0) for day in all_days]
    unique_counts = [len(daily_players.get(day, set())) for day in all_days]

    # Plot
    plt.figure(figsize=(40, 12))
    plt.plot(all_days, total_counts, marker="o", label="Total Plays")
    plt.plot(all_days, unique_counts, marker="s", label="Unique Players")

    plt.title(f"{game_dict[game]} Daily Player Statistics", fontsize=14)
    plt.xlabel("Date (Daily)", fontsize=10)
    plt.ylabel("Count", fontsize=10)

    plt.gca().yaxis.set_major_locator(ticker.MultipleLocator(500))

    # Reduce label frequency if many days
    if len(all_days) > 60:
        plt.xticks(all_days[::7])  # show one label per week
    else:
        plt.xticks(rotation=60, fontsize=8)

    plt.xticks(rotation=60, fontsize=8)
    plt.yticks(fontsize=8)

    y_min, y_max = plt.ylim()

    # text labels
    for i, day in enumerate(all_days):
        if total_counts[i] > 0:
            plt.text(
                day, total_counts[i] + (y_max * 0.02),
                str(total_counts[i]), ha="center", fontsize=7
            )
        if unique_counts[i] > 0:
            plt.text(
                day, unique_counts[i] - (y_max * 0.02),
                str(unique_counts[i]), ha="center", fontsize=7
            )

    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    plt.savefig(f"{game}/{game_dict[game]}_daily_players_20260101.png")
    plt.show()

game = "StarWarsUnlimited"
# game = "Lorcana"
players_filename = f"{game}/players.csv"
plot(players_filename)