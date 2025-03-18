import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors

def load_data(influencer_path, brand_path):
    """
    Load influencer and brand data from CSV files.
    """
    influencer_df = pd.read_csv(influencer_path)
    brand_df = pd.read_csv(brand_path)
    print("Available columns in brand_df:", brand_df.columns.tolist())
    return influencer_df, brand_df

def validate_brand_columns(brand_df, brand_column='brand_name'):
    """
    Ensure the required brand column exists.
    """
    if brand_column not in brand_df.columns:
        possible_columns = [col for col in brand_df.columns if 'brand' in col.lower()]
        raise KeyError(
            f"'{brand_column}' column not found. Available columns with 'brand': {possible_columns}"
        )

def preprocess_features(df, features):
    """
    Extract and fill missing values for the given features.
    """
    return df[features].fillna(0)

def get_recommendations(brand_df, influencer_df, features, n_neighbors=5):
    """
    Compute the nearest neighbors for each influencer based on selected features.
    
    Returns a dictionary mapping each influencer username to a list of recommended 
    brands along with the corresponding Euclidean distances.
    """
    # Preprocess features for both dataframes
    brand_features = preprocess_features(brand_df, features)
    influencer_features = preprocess_features(influencer_df, features)
    
    # Standardize features
    scaler = StandardScaler()
    brand_features_scaled = scaler.fit_transform(brand_features)
    influencer_features_scaled = scaler.transform(influencer_features)
    
    # Fit the Nearest Neighbors model on brand features
    nn_model = NearestNeighbors(n_neighbors=n_neighbors, metric="euclidean")
    nn_model.fit(brand_features_scaled)
    
    # Find the nearest neighbors for each influencer
    distances, indices = nn_model.kneighbors(influencer_features_scaled)
    
    recommendations = {}
    if 'username' not in influencer_df.columns:
        raise KeyError("'username' column not found in influencer_df")
        
    for i, influencer in influencer_df.iterrows():
        influencer_username = influencer["username"]
        recs = []
        for d, idx in zip(distances[i], indices[i]):
            brand_name = brand_df.iloc[idx]["brand_name"]
            recs.append({"brand_name": brand_name, "distance": d})
        recommendations[influencer_username] = recs
        
    return recommendations

def save_recommendations(recommendations, output_file):
    """
    Save the recommendations to a CSV file.
    """
    rows = []
    for influencer, recs in recommendations.items():
        for rec in recs:
            rows.append({
                "influencer": influencer,
                "recommended_brand": rec["brand_name"],
                "distance": rec["distance"]
            })
    df = pd.DataFrame(rows)
    df.to_csv(output_file, index=False)
    print(f"Recommendations saved to {output_file}")

def evaluate_recommendations(recommendations, ground_truth):
    """
    Evaluate recommendations against ground truth data.
    
    ground_truth should be a dictionary mapping influencer usernames to a set 
    of true brand names.
    
    Returns the accuracy (fraction of influencers with at least one correct recommendation).
    """
    correct_count = 0
    total_influencers = len(recommendations)
    for influencer, recs in recommendations.items():
        recommended_brands = [rec["brand_name"] for rec in recs]
        true_brands = ground_truth.get(influencer, set())
        # Count as correct if any recommended brand is in the ground truth.
        if any(brand in true_brands for brand in recommended_brands):
            correct_count += 1
    accuracy = correct_count / total_influencers if total_influencers > 0 else 0
    return accuracy

def main():
    # File paths
    influencer_path = r"C:\project\influenceHub\influencerData.csv"
    brand_path = r"C:\project\influenceHub\brandData.csv"
    
    # Load the data
    influencer_df, brand_df = load_data(influencer_path, brand_path)
    
    # Validate that the required column exists in the brand dataframe
    validate_brand_columns(brand_df, brand_column='brand_name')
    
    # Define the common features to use for similarity
    features = [
        "followers",
        "engagement_score",  # Ensure the column name matches your CSV
        "engagement_per_follower",
        "follower_ratio",
        "estimated_reach",
        "estimated_impression",
        "reach_ratio",
        "avg_likes_computed",
        "avg_comments_computed"
    ]
    
    # Generate recommendations for each influencer
    recommendations = get_recommendations(brand_df, influencer_df, features, n_neighbors=5)
    
    # Display the recommendations along with the distances
    print("=== Brand Recommendations for Each Influencer ===")
    for influencer, recs in recommendations.items():
        print(f"Influencer: {influencer}")
        for rec in recs:
            print(f"  Brand: {rec['brand_name']}, Distance: {rec['distance']:.4f}")
        print("-" * 40)
    
    # Save recommendations to a CSV file
    save_recommendations(recommendations, "brand_recommendations.csv")
    
    # Define ground truth for evaluation (populate with your actual data if available)
    ground_truth = {
        # Example:
        # "virat.kohli": {"Nike", "Adidas"},
        # "bhuvan.bam22": {"Puma"}
    }
    
    # Evaluate recommendations if ground truth data is available
    if ground_truth:
        accuracy = evaluate_recommendations(recommendations, ground_truth)
        print("Accuracy:", accuracy)
    else:
        print("Ground truth data not provided. Skipping evaluation.")

if __name__ == "__main__":
    main()
