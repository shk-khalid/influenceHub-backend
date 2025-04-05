import os
import re
import json
import traceback
import numpy as np
import pandas as pd
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from tensorflow.keras.models import load_model  # type: ignore
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
from brands_insightapp.models import BrandsSocialStats, Brand
from authapp.models import InstaStats, BrandSuggestion
from brands_insightapp.serializers import BrandDetailSerializer
from .serializers import SuggestionHistorySerializer


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


class TrainAndEvaluateView(APIView):
    """
    POST endpoint that trains, evaluates, and saves the DEC and encoder models.
    Loads data from static CSV files, pretrains the autoencoder, initializes and trains DEC,
    evaluates the model on a test split, and saves the models in the native Keras format.
    """
    def post(self, request, format=None):
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
            dec_model_path = os.path.join(saved_model_dir, 'dec_model.keras')
            encoder_model_path = os.path.join(saved_model_dir, 'encoder_model.keras')
            dec_model.save(dec_model_path)
            encoder_model.save(encoder_model_path)

            response_data = {
                "message": "Model trained, evaluated, and saved successfully. Alhamdulillah!",
                "evaluation": evaluation_results,
                "loss_history": loss_history[-5:],
                "model_paths": {
                    "dec_model": dec_model_path,
                    "encoder_model": encoder_model_path
                }
            }
            return Response(convert_numpy_types(response_data), status=status.HTTP_200_OK)
        except Exception as e:
            error_message = traceback.format_exc()
            return Response({"error": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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


class SuggestBrandsView(APIView):
    """
    GET endpoint that fetches influencer metrics from the authenticated user's InstaStats record,
    computes additional metrics (if needed), and suggests brands based on cosine similarity (>= 0.95).
    Brands that the user has already accepted or declined are filtered out.
    Returns a detailed brand serializer.
    """
    def get(self, request, format=None):
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            # Extract the Instagram handle from socialLinks
            social_links = request.user.socialLinks
            if isinstance(social_links, str):
                social_links = json.loads(social_links)
            insta_url = social_links.get("instagram", "")
            # Extract the handle from a URL like "https://www.instagram.com/filmthusiast/"
            match = re.search(r'instagram\.com/([^/]+)/?', insta_url)
            if match:
                insta_handle = match.group(1)
            else:
                insta_handle = request.user.username

            # Lookup InstaStats using the extracted handle (case-insensitive)
            try:
                insta_stats = InstaStats.objects.get(userName__iexact=insta_handle)
            except InstaStats.DoesNotExist:
                return Response({"error": "User InstaStats not found."}, status=status.HTTP_404_NOT_FOUND)

            # Compute influencer metrics from posts
            posts = insta_stats.posts.all()  # Assumes related_name="posts" in InstaPost model
            total_likes, total_comments, count = 0, 0, 0
            for post in posts:
                if post.post_detail:
                    like_count = post.post_detail.get("likeCount")
                    comment_count = post.post_detail.get("commentCount")
                    if like_count is not None and comment_count is not None:
                        total_likes += float(like_count)
                        total_comments += float(comment_count)
                        count += 1
            avg_likes_computed = total_likes / count if count > 0 else 0
            avg_comments_computed = total_comments / count if count > 0 else 0

            followers = insta_stats.followers
            verified_multiplier = 1.2 if insta_stats.is_verified else 1.0
            professional_multiplier = 1.1 if getattr(insta_stats, "is_professional", False) else 1.0

            estimated_reach = ((followers ** 0.6) *
                               ((avg_likes_computed + avg_comments_computed) ** 0.4) *
                               verified_multiplier * professional_multiplier * 100)
            estimated_impression = estimated_reach * 1.5
            reach_ratio = estimated_reach / followers if followers > 0 else 0
            engagement_score = (avg_likes_computed * 0.7) + (avg_comments_computed * 0.3)
            engagement_per_follower = ((avg_likes_computed + avg_comments_computed) / followers) if followers > 0 else np.nan

            influencer_data = {
                "followers": followers,
                "engagement_score": engagement_score,
                "engagement_per_follower": engagement_per_follower,
                "estimated_reach": estimated_reach,
                "estimated_impression": estimated_impression,
                "reach_ratio": reach_ratio,
                "avg_likes_computed": avg_likes_computed,
                "avg_comments_computed": avg_comments_computed
            }
            
            influencer_df = pd.DataFrame([influencer_data])
            # Only these features were used during training
            required_fields = [
                "followers", "engagement_score", "engagement_per_follower",
                "estimated_reach", "estimated_impression", "reach_ratio"
            ]
            
            # Retrieve brand social stats used during training, including brand id and name
            qs = BrandsSocialStats.objects.all().values(*required_fields, "brand__name", "brand__id")
            df_brands = pd.DataFrame(list(qs))
            if df_brands.empty:
                return Response({"error": "No brand data available."}, status=status.HTTP_404_NOT_FOUND)
            
            # Exclude brands that have already been suggested
            existing_suggestions = BrandSuggestion.objects.filter(user=request.user).values_list("brand__id", flat=True)
            df_brands = df_brands[~df_brands["brand__id"].isin(existing_suggestions)]
            
            # Fit a scaler on brand data for normalization using only the required fields
            scaler = StandardScaler()
            scaler.fit(df_brands[required_fields])
            
            # Transform influencer data using only the required fields
            influencer_scaled = scaler.transform(influencer_df[required_fields])
            encoder = load_encoder_model()
            influencer_latent = encoder.predict(influencer_scaled)
            
            # Transform brand data
            brands_array = scaler.transform(df_brands[required_fields].values)
            brands_latent = encoder.predict(brands_array)
            
            # Compute cosine similarities for each brand
            similarities = [
                cosine_similarity(influencer_latent.flatten(), brands_latent[i].flatten())
                for i in range(brands_latent.shape[0])
            ]
            df_brands["similarity"] = similarities
            
            # Filter and sort brands with similarity >= 0.95
            df_filtered_sorted = df_brands[df_brands["similarity"] >= 0.95].sort_values(by="similarity", ascending=False)
            
            # Extract ordered list of brand IDs from the filtered dataframe
            suggested_ids = list(df_filtered_sorted["brand__id"])
            suggested_count = len(suggested_ids)
            
            # Query the Brand model to get the full details
            # To preserve order, we fetch each brand by ID in the suggested order.
            brands = [Brand.objects.get(id=bid) for bid in suggested_ids]
            serializer = BrandDetailSerializer(brands, many=True)
            
            response_data = {
                "user_profile_metrics": influencer_data,
                "suggested_count": suggested_count,
                "suggested_brands": serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class RespondBrandSuggestionView(APIView):
    
    def post(self, request, brand_id, format=None):
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        action = request.data.get('action')
        if action not in ('accept', 'decline'):
            return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return Response({"error": "Brand not found."}, status=status.HTTP_404_NOT_FOUND)

        # Create or update the suggestion record
        BrandSuggestion.objects.update_or_create(
            user=request.user,
            brand=brand,
            defaults={'status': action}
        )

        return Response(
            {"message": f"Brand {action}ed successfully."},
            status=status.HTTP_200_OK
        )
    
class SuggestionHistoryView(APIView):
    """
    GET /api/suggestions/history/
    Returns the list of brands this user has accepted or declined, with details.
    """
    def get(self, request, format=None):
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        qs = BrandSuggestion.objects.filter(user=request.user).order_by('-suggested_at')
        serializer = SuggestionHistorySerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)