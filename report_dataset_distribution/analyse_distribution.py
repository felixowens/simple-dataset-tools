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
    captions: list[str],
    concept: str,
    categories: list[str],
    filenames: list[str] | None = None,
):
    """
    Analyze the distribution of a concept across different categories in captions.

    Args:
        captions: List of captions to analyze
        concept: The concept to analyze (e.g., "hair")
        categories: List of categories to look for (e.g., ["long", "medium", "short"])
        filenames: Optional list of filenames corresponding to captions

    Returns:
        DataFrame with distribution statistics and lists of filenames with missing/unspecified categories
    """

    # Initialize counters
    results = Counter()
    total_samples = len(captions)

    # Initialize results with all categories and "missing"
    for category in categories:
        results[category] = 0
    results["unspecified"] = 0

    # Sort categories by length (descending) to prioritize longer matches
    sorted_categories = sorted(categories, key=len, reverse=True)

    # Pattern to match concept paired with each category
    patterns = {
        category: re.compile(
            rf"\b{category}\s+{concept}\b|\b{concept}\s+{category}\b", re.IGNORECASE
        )
        for category in sorted_categories
    }

    # Check for concept without any category
    concept_pattern = re.compile(rf"\b{concept}\b", re.IGNORECASE)

    # Track filenames with missing or unspecified categories
    missing_files = []
    unspecified_files = []

    # Count occurrences
    for i, caption in enumerate(captions):
        category_found = False

        for category, pattern in patterns.items():
            if pattern.search(caption):
                results[category] += 1
                category_found = True
                break

        # If concept is mentioned but without any specified category
        if not category_found and concept_pattern.search(caption):
            results["unspecified"] += 1
            if filenames:
                unspecified_files.append(filenames[i])
        # If concept is not mentioned at all
        elif not category_found:
            if filenames:
                missing_files.append(filenames[i])

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

    return result_df, total_samples, missing_files, unspecified_files


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


def calculate_balance_recommendations(result_df, total_samples):
    """
    Calculate recommendations for how many samples to add to achieve a balanced dataset.

    Args:
        result_df: DataFrame with distribution statistics
        total_samples: Total number of samples in the dataset

    Returns:
        DataFrame with recommendations for each category
    """
    # Filter out 'missing' and 'unspecified' categories for balancing purposes
    categories_df = result_df[~result_df["category"].isin(["missing", "unspecified"])]

    if len(categories_df) == 0:
        return pd.DataFrame()  # No categories to balance

    # Find the category with the highest count
    max_count = categories_df["count"].max()

    # Calculate how many samples to add for each category
    recommendations = []
    for _, row in categories_df.iterrows():
        category = row["category"]
        current_count = row["count"]
        to_add = max_count - current_count

        recommendations.append(
            {
                "category": category,
                "current_count": current_count,
                "target_count": max_count,
                "samples_to_add": to_add,
                "percentage_increase": (
                    (to_add / current_count * 100)
                    if current_count > 0
                    else float("inf")
                ),
            }
        )

    return pd.DataFrame(recommendations)


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
    parser.add_argument(
        "--output-dir", default="testing", help="Directory to save output files"
    )

    args = parser.parse_args()

    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    data_loader = CaptionDataLoader()
    data_loader.load_from_json_custom(args.captions_file)

    filenames = list(data_loader.dict.keys()) if hasattr(data_loader, "dict") else None

    result_df, total_samples, missing_files, unspecified_files = (
        analyze_concept_distribution(
            data_loader.captions, args.concept, args.categories, filenames
        )
    )

    # Print text summary
    print(
        f"\nAnalysis of '{args.concept}' in {total_samples} captions with categories: {', '.join(args.categories)}"
    )
    print("-" * 50)

    sorted_df = visualize_distribution(result_df, args.concept, total_samples)

    # Calculate balance recommendations
    recommendations_df = calculate_balance_recommendations(sorted_df, total_samples)

    # Print recommendations
    if not recommendations_df.empty:
        print(
            "\nBased on the analysis, we recommend you to add the following number of extra samples for each category to achieve a balanced dataset:"
        )
        print("-" * 100)
        for _, row in recommendations_df.iterrows():
            if row["samples_to_add"] > 0:
                print(
                    f"  {row['category']}: {int(row['samples_to_add'])} samples (from {int(row['current_count'])} to {int(row['target_count'])} samples, {row['percentage_increase']:.1f}% increase)"
                )

        # Save recommendations to CSV
        recommendations_file = (
            output_dir / f"{args.concept}_balance_recommendations.csv"
        )
        recommendations_df.to_csv(recommendations_file, index=False)
        print(f"\nDetailed recommendations saved to {recommendations_file}")

    # Save results to CSV
    output_file = output_dir / f"{args.concept}_distribution.csv"
    sorted_df.to_csv(output_file, index=False)

    # Save missing and unspecified filenames to text files
    if missing_files:
        missing_file = output_dir / f"{args.concept}_missing_files.txt"
        with open(missing_file, "w") as f:
            f.write("\n".join(missing_files))
        print(f"Found {len(missing_files)} files without the concept '{args.concept}'")
        print(f"List saved to {missing_file}")

    if unspecified_files:
        unspecified_file = output_dir / f"{args.concept}_unspecified_files.txt"
        with open(unspecified_file, "w") as f:
            f.write("\n".join(unspecified_files))
        print(
            f"Found {len(unspecified_files)} files with unspecified '{args.concept}' category"
        )
        print(f"List saved to {unspecified_file}")

    print(
        f"\nResults saved to {output_file} and {output_dir}/{args.concept}_distribution.png"
    )


if __name__ == "__main__":
    main()

    # Example usage:
    # python analyse_distribution.py /path/to/captions.json "hair" "long" "medium" "short"
