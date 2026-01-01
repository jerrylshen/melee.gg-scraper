import csv
from collections import Counter, defaultdict
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.ticker as ticker


def plot(filename):

    game_dict = {
        "StarWarsUnlimited": "SWU",
        "Lorcana": "LORCANA"
    }

    month_counts = Counter()
    monthly_players = defaultdict(set)  # key: month (YYYY-MM), value: set of unique player URLs or names

    with open(filename, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            date_str = row["DATE"]
            try:
                date = datetime.strptime(date_str.strip(), "%Y/%m/%d")

                # --- Only include data starting from Jan 2024 ---
                if date < datetime(2024, 1, 1) or date > datetime.now():
                    continue

                if date.year < 2024 or date.year > datetime.now().year:
                    continue

                month_key = date.strftime("%Y-%m")
                month_counts[month_key] += 1

                player_id = row["PLAYER_NAME"].strip()
                monthly_players[month_key].add(player_id)

            except ValueError:
                continue

    # Create full month range
    if not month_counts:
        raise ValueError("No valid date data found.")

    min_month = min(datetime.strptime(m, "%Y-%m") for m in month_counts)
    max_month = max(datetime.strptime(m, "%Y-%m") for m in month_counts)

    all_months = pd.date_range(start=min_month, end=max_month, freq="MS").strftime("%Y-%m").tolist()

    # Fill counts
    total_counts = [month_counts.get(month, 0) for month in all_months]
    unique_counts = [len(monthly_players.get(month, set())) for month in all_months]

    # Plot
    plt.figure(figsize=(24, 12))
    plt.plot(all_months, total_counts, marker="o", label="Total Plays")
    plt.plot(all_months, unique_counts, marker="s", color="orange", label="Unique Players")

    plt.title(f"{game_dict[game]} Monthly Player Statistics", fontsize=12)
    plt.xlabel("Month", fontsize=10)
    plt.ylabel("Count", fontsize=10)

    plt.gca().yaxis.set_major_locator(ticker.MultipleLocator(1000))

    plt.xticks(rotation=45, fontsize=8)
    plt.yticks(fontsize=8)

    for i, month in enumerate(all_months):
        if total_counts[i] > 0:
            plt.text(month, total_counts[i] + 50, str(total_counts[i]), ha="center", va="bottom", fontsize=10, color="blue")
        if unique_counts[i] > 0:
            plt.text(month, unique_counts[i] + 50, str(unique_counts[i]), ha="center", va="bottom", fontsize=10, color="orange")

    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    plt.savefig(f"{game}/{game_dict[game]}_monthly_players_20260101.png")
    plt.show()


game = "StarWarsUnlimited"
# game = "Lorcana"
players_filename = f"{game}/players.csv"
plot(players_filename)