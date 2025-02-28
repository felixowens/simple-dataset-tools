from dataloader import CaptionDataLoader


def analyze_concept_distribution(caption_dataset, concept, categories):
    """
    Analyzes the distribution of concept categories in a caption dataset.

    Args:
        caption_dataset (list of str): A list of captions (strings).
        concept (str): The main concept to analyze (e.g., "hair").
        categories (list of str): A list of categories related to the concept
                                  (e.g., ["long", "medium", "short", "very short"]).

    Returns:
        dict: A dictionary containing the distribution of categories and missing instances.
              Keys are category names (and "missing"), values are dictionaries with
              "count" and "percentage".
    """

    category_counts = {
        category.lower(): 0 for category in categories
    }  # Initialize counts for each category to 0, lowercased for case-insensitive matching
    category_counts["missing"] = (
        0  # Count for captions where the concept is missing in any category.
    )

    total_captions = len(caption_dataset)

    if not total_captions:
        return {
            category: {"count": 0, "percentage": 0.0} for category in category_counts
        }  # Handle empty dataset

    for caption in caption_dataset:
        caption_lower = caption.lower()  # For case-insensitive matching
        found_category = False  # Flag to track if any category is found in the caption

        for category in categories:
            category_lower = category.lower()  # Lowercase the category for matching
            if (
                category_lower in caption_lower
            ):  # Simple substring check, can be improved for more sophisticated matching
                category_counts[category_lower] += 1
                found_category = True
                break  # Assume only one category per concept instance in a caption, can be adjusted if needed

        if not found_category:
            category_counts["missing"] += 1

    distribution_report = {}
    for category, count in category_counts.items():
        percentage = (count / total_captions) * 100 if total_captions > 0 else 0.0
        distribution_report[category] = {"count": count, "percentage": percentage}

    return distribution_report


def main():
    """
    Main function to demonstrate the concept distribution analysis.
    """
    data_loader = CaptionDataLoader()
    data_loader.load_from_json_custom(
        "/home/felix/Downloads/scl-caption-tiny_json(3).json"
    )
    caption_data = data_loader.captions

    concept_to_analyze = "ass"
    categories = ["small, average, big, very big, huge"]

    distribution = analyze_concept_distribution(
        caption_data, concept_to_analyze, categories
    )

    print(f"Concept Distribution Analysis for '{concept_to_analyze}':")
    print("-" * 40)
    for category, data in distribution.items():
        print(f"Category: {category.capitalize()}")
        print(f"  Count: {data['count']}")
        print(f"  Percentage: {data['percentage']:.2f}%")
        print("-" * 20)


if __name__ == "__main__":
    main()
