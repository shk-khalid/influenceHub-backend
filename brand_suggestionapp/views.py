import os
import json
import traceback
import numpy as np
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from tensorflow.keras.models import load_model # type: ignore
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from .algorithm import (
    load_and_prepare_data,
    pretrain_autoencoder,
    initialize_dec,
    build_dec_model,
    train_dec_model,
    evaluate_dec
)
from brands_insightapp.models import BrandsSocialStats

def convert_numpy_types(obj):
    """Recursively convert NumPy types in the object to native Python types."""
    if isinstance(obj, np.generic):
        return obj.item()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    else:
        return obj

@csrf_exempt
def train_and_evaluate(request):
    """
    Trains, evaluates, and saves the DEC model and encoder model.
    Loads data from static CSV files, pretrains the autoencoder, initializes and trains DEC,
    evaluates the model on a test split, and saves the models in the native Keras format.
    """
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        dataset_path_brands = os.path.join(base_dir, 'data', 'brandData.csv')
        dataset_path_influencers = os.path.join(base_dir, 'data', 'influencerData.csv')
        df_combined, X_scaled, common_features = load_and_prepare_data(dataset_path_brands, dataset_path_influencers)
        
        X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
            X_scaled, df_combined['true_label'].values, df_combined.index,
            test_size=0.3, random_state=42, stratify=df_combined['true_label']
        )
        
        input_dim = X_train.shape[1]
        latent_dim = 4
        
        autoencoder, encoder_model = pretrain_autoencoder(X_train, input_dim, latent_dim)
        cluster_centers, _ = initialize_dec(encoder_model, X_train)
        dec_model = build_dec_model(encoder_model, n_clusters=2, cluster_centers=cluster_centers)
        loss_history = train_dec_model(dec_model, X_train)
        evaluation_results = evaluate_dec(encoder_model, dec_model, X_test, df_combined, idx_test)
        
        saved_model_dir = os.path.join(base_dir, 'saved_models')
        if not os.path.exists(saved_model_dir):
            os.makedirs(saved_model_dir)
        # Save the models using the native Keras format
        dec_model.save(os.path.join(saved_model_dir, 'dec_model.keras'))
        encoder_model.save(os.path.join(saved_model_dir, 'encoder_model.keras'))
        
        response = {
            "message": "Model trained, evaluated, and saved successfully. Alhamdulillah!",
            "evaluation": evaluation_results,
            "loss_history": loss_history[-5:],
            "model_paths": {
                "dec_model": os.path.join(saved_model_dir, 'dec_model.keras'),
                "encoder_model": os.path.join(saved_model_dir, 'encoder_model.keras')
            }
        }
        return JsonResponse(convert_numpy_types(response))
    except Exception as e:
        error_message = traceback.format_exc()
        return JsonResponse({"error": error_message}, status=500)

# Global variables for caching the encoder model and scaler
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVED_MODELS_DIR = os.path.join(BASE_DIR, 'saved_models')
ENCODER_MODEL_PATH = os.path.join(SAVED_MODELS_DIR, 'encoder_model.keras')

encoder_model = None
scaler = None

def load_encoder_model():
    """Load the saved encoder model from disk (cached globally)."""
    global encoder_model
    if encoder_model is None:
        encoder_model = load_model(ENCODER_MODEL_PATH, compile=False)
    return encoder_model

def get_scaler():
    """
    Returns a StandardScaler fitted on brand social metrics from BrandsSocialStats.
    The features used are: followers, engagement_score, engagement_per_follower, 
    estimated_reach, estimated_impression, reach_ratio.
    """
    global scaler
    qs = BrandsSocialStats.objects.all().values(
        'followers', 'engagement_score', 'engagement_per_follower',
        'estimated_reach', 'estimated_impression', 'reach_ratio'
    )
    df = pd.DataFrame(list(qs))
    if df.empty:
        scaler = StandardScaler()
    else:
        features = ['followers', 'engagement_score', 'engagement_per_follower',
                    'estimated_reach', 'estimated_impression', 'reach_ratio']
        scaler = StandardScaler().fit(df[features])
    return scaler

def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return np.dot(a, b) / (a_norm * b_norm)

@csrf_exempt
def suggest_brands(request):
    """
    Suggests brands based on influencer metrics.
    Expects a POST request with influencer metrics in JSON and returns only those brands with a
    cosine similarity of 0.95 or higher, along with the count of suggested brands.
    """
    if request.method != 'POST':
        return JsonResponse({"error": "POST request required"}, status=400)
    
    try:
        data = json.loads(request.body)
        required_fields = [
            'followers', 'engagement_score', 'engagement_per_follower',
            'estimated_reach', 'estimated_impression', 'reach_ratio'
        ]
        if not all(field in data for field in required_fields):
            return JsonResponse({"error": "Missing required influencer metrics."}, status=400)

        # Convert influencer metrics to a DataFrame
        influencer_df = pd.DataFrame([data])
        
        # Retrieve brand social stats from the database
        qs = BrandsSocialStats.objects.all().values(*required_fields, 'brand__name')
        df_brands = pd.DataFrame(list(qs))
        if df_brands.empty:
            return JsonResponse({"error": "No brand data available."}, status=404)
        
        # Fit a new scaler on the brand data
        scaler = StandardScaler()
        scaler.fit(df_brands[required_fields])
        
        # Scale influencer metrics and obtain latent representation using the encoder model
        influencer_scaled = scaler.transform(influencer_df)
        encoder = load_encoder_model()
        influencer_latent = encoder.predict(influencer_scaled)
        
        # Scale brand metrics and compute latent representations
        brands_array = scaler.transform(df_brands[required_fields].values)
        brands_latent = encoder.predict(brands_array)
        
        # Compute cosine similarity between influencer and each brand
        similarities = [cosine_similarity(influencer_latent.flatten(), brands_latent[i].flatten())
                        for i in range(brands_latent.shape[0])]
        df_brands['similarity'] = similarities
        
        # Filter and sort brands with similarity >= 0.95
        df_filtered_sorted = df_brands[df_brands['similarity'] >= 0.95].sort_values(by='similarity', ascending=False)
        
        suggested_brands = df_filtered_sorted.to_dict(orient='records')
        suggested_count = len(suggested_brands)
        response = {
            "influencer_metrics": data,
            "suggested_count": suggested_count,
            "suggested_brands": suggested_brands
        }
        return JsonResponse(response)
    
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
