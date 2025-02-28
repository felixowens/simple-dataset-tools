from typing import cast
import pandas as pd
import re
import argparse
from pathlib import Path
from collections import Counter
import matplotlib.pyplot as plt
import seaborn as sns

from dataloader import CaptionDataLoader


def analyze_concept_distribution(
    captions: list[str], concept: str, categories: list[str]
):
    """
    Analyze the distribution of a concept across different categories in captions.

    Args:
        captions: List of captions to analyze
        concept: The concept to analyze (e.g., "hair")
        categories: List of categories to look for (e.g., ["long", "medium", "short"])

    Returns:
        DataFrame with distribution statistics
    """

    # Initialize counters
    results = Counter()
    total_samples = len(captions)

    # Initialize results with all categories and "missing"
    for category in categories:
        results[category] = 0
    results["unspecified"] = 0

    # Pattern to match concept paired with each category
    patterns = {
        category: re.compile(
            rf"\b{category}\s+{concept}\b|\b{concept}\s+{category}\b", re.IGNORECASE
        )
        for category in categories
    }

    # Check for concept without any category
    concept_pattern = re.compile(rf"\b{concept}\b", re.IGNORECASE)

    # Count occurrences
    for caption in captions:
        category_found = False

        for category, pattern in patterns.items():
            if pattern.search(caption):
                results[category] += 1
                category_found = True
                break

        # If concept is mentioned but without any specified category
        if not category_found and concept_pattern.search(caption):
            results["unspecified"] += 1

    # Count captions without the concept at all
    results["missing"] = total_samples - sum(results.values())

    # Create DataFrame for the results
    result_df = pd.DataFrame(
        {
            "category": list(results.keys()),
            "count": list(results.values()),
            "percentage": [count / total_samples * 100 for count in results.values()],
        }
    )

    return result_df, total_samples


def visualize_distribution(result_df, concept, total_samples):
    """Create visualization of the concept distribution"""
    plt.figure(figsize=(10, 6))

    # Sort by count in descending order, except put "missing" at the end if it exists
    if "missing" in result_df["category"].values:
        temp_df = result_df[result_df["category"] != "missing"]
        missing_df = result_df[result_df["category"] == "missing"]
        sorted_df = pd.concat(
            [temp_df.sort_values("count", ascending=False), missing_df]
        )
    else:
        sorted_df = result_df.sort_values("count", ascending=False)

    # Create the bar plot with percentages
    sns.barplot(
        x="category", y="percentage", data=sorted_df, palette="viridis", hue="category"
    )

    # Add percentage labels on top of each bar
    for i, row in enumerate(sorted_df.itertuples()):
        plt.text(
            i,
            cast(float, row.percentage) + 1,
            f"{row.percentage:.1f}%",
            ha="center",
            fontweight="bold",
        )

    plt.title(f'Distribution of "{concept}" across {total_samples} captions')
    plt.ylabel("Percentage (%)")
    plt.xlabel("Category")
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Save and show the visualization
    plt.savefig(f"testing/{concept}_distribution.png")

    return sorted_df


def main():
    parser = argparse.ArgumentParser(
        description="Analyze concept distribution in captions"
    )
    parser.add_argument("captions_file", help="Path to the captions file")
    parser.add_argument("concept", help='Concept to analyze (e.g., "hair")')
    parser.add_argument(
        "categories",
        nargs="+",
        help='Categories to analyze (e.g., "long medium short")',
    )

    args = parser.parse_args()

    data_loader = CaptionDataLoader()
    data_loader.load_from_json_custom(args.captions_file)

    result_df, total_samples = analyze_concept_distribution(
        data_loader.captions, args.concept, args.categories
    )

    # Print text summary
    print(
        f"\nAnalysis of '{args.concept}' in {total_samples} captions with categories: {', '.join(args.categories)}"
    )
    print("-" * 50)

    sorted_df = visualize_distribution(result_df, args.concept, total_samples)

    # Save results to CSV
    output_file = f"testing/{args.concept}_distribution.csv"
    sorted_df.to_csv(output_file, index=False)
    print(
        f"\nResults saved to {output_file} and testing/{args.concept}_distribution.png"
    )


if __name__ == "__main__":
    main()

    # Example usage:
    # python analyse_distribution.py /path/to/captions.json "hair" "long" "medium" "short"

    # TODO: handle caption overlap between categories, should first lok for the longest match
    # TODO: add var to return dict of filename and caption to dataloader
    # TODO: report which filenames have missing or unspecified categories
