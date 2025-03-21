import os
import pandas as pd  
import numpy as np  
import tensorflow as tf  
from tensorflow.keras.models import Model  # type: ignore
from tensorflow.keras.layers import Input, Dense   # type: ignore
from tensorflow.keras.optimizers import Adam   # type: ignore
from tensorflow.keras import backend as K   # type: ignore
from sklearn.preprocessing import StandardScaler  
from sklearn.cluster import KMeans  
from sklearn.metrics import silhouette_score, confusion_matrix  
from sklearn.model_selection import train_test_split  
from scipy.optimize import linear_sum_assignment  
import matplotlib.pyplot as plt

# Custom clustering layer for DEC with serialization support
class ClusteringLayer(tf.keras.layers.Layer):  
    def __init__(self, n_clusters, weights=None, alpha=1.0, **kwargs):  
        super(ClusteringLayer, self).__init__(**kwargs)  
        self.n_clusters = n_clusters  
        self.alpha = alpha  
        self.initial_weights = weights  
  
    def build(self, input_shape):  
        self.input_dim = input_shape[1]  
        self.clusters = self.add_weight(
            shape=(self.n_clusters, self.input_dim),  
            initializer='glorot_uniform',  
            name='clusters'
        )  
        if self.initial_weights is not None:  
            self.set_weights([self.initial_weights])  
            del self.initial_weights  
        super(ClusteringLayer, self).build(input_shape)  
  
    def call(self, inputs, **kwargs):  
        q = 1.0 / (1.0 + (K.sum(K.square(K.expand_dims(inputs, axis=1) - self.clusters), axis=2) / self.alpha))  
        q **= (self.alpha + 1.0) / 2.0  
        return q / K.sum(q, axis=1, keepdims=True)  
  
    def get_config(self):  
        config = super(ClusteringLayer, self).get_config()  
        config.update({  
            "n_clusters": self.n_clusters,  
            "alpha": self.alpha  
        })  
        return config

def load_and_prepare_data(dataset_path_brands, dataset_path_influencers):
    # Load CSV data and combine brands and influencers
    df_brands = pd.read_csv(dataset_path_brands)
    df_influencers = pd.read_csv(dataset_path_influencers)
    common_features = [  
        'followers', 'engagement_score', 'engagement_per_follower',  
        'estimated_reach', 'estimated_impression', 'reach_ratio'  
    ]
    df_brands['entity_type'] = 'brand'
    df_brands['entity_name'] = df_brands['brand_name']
    df_influencers['entity_type'] = 'influencer'
    df_influencers['entity_name'] = df_influencers['Influencer']
    df_brands_sel = df_brands[common_features + ['entity_type', 'entity_name']]
    df_influencers_sel = df_influencers[common_features + ['entity_type', 'entity_name']]
    df_combined = pd.concat([df_brands_sel, df_influencers_sel], ignore_index=True)
    label_mapping = {'brand': 0, 'influencer': 1}
    df_combined['true_label'] = df_combined['entity_type'].map(label_mapping)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_combined[common_features].values)
    return df_combined, X_scaled, common_features

def pretrain_autoencoder(X_train, input_dim, latent_dim=4, epochs=50, batch_size=16):
    # Build and train a simple autoencoder
    input_layer = Input(shape=(input_dim,))
    encoder = Dense(8, activation='relu')(input_layer)
    latent = Dense(latent_dim, activation='relu')(encoder)
    decoder = Dense(8, activation='relu')(latent)
    output_layer = Dense(input_dim, activation='linear')(decoder)
    autoencoder = Model(inputs=input_layer, outputs=output_layer)
    autoencoder.compile(optimizer=Adam(learning_rate=1e-3), loss='mse')
    autoencoder.fit(X_train, X_train, epochs=epochs, batch_size=batch_size, shuffle=True, verbose=1)
    encoder_model = Model(inputs=input_layer, outputs=latent)
    return autoencoder, encoder_model

def initialize_dec(encoder_model, X_train, n_clusters=2):
    # Compute latent representations and initialize cluster centers via KMeans
    X_latent_train = encoder_model.predict(X_train)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    kmeans.fit(X_latent_train)
    return kmeans.cluster_centers_, X_latent_train

def build_dec_model(encoder_model, n_clusters, cluster_centers):
    # Build the DEC model by adding the clustering layer to the encoder's output
    latent = encoder_model.output
    clustering_layer = ClusteringLayer(n_clusters, weights=cluster_centers, name='clustering')(latent)
    dec_model = Model(inputs=encoder_model.input, outputs=clustering_layer)
    dec_model.compile(optimizer=Adam(learning_rate=1e-3), loss='kld')
    return dec_model

def train_dec_model(dec_model, X_train, maxiter=1000, update_interval=140):
    # Train DEC with iterative updates of the target distribution
    def target_distribution(q):  
        weight = q ** 2 / np.sum(q, axis=0)
        return (weight.T / np.sum(weight, axis=1)).T
    
    loss_history = []
    for ite in range(maxiter):
        if ite % update_interval == 0:
            q = dec_model.predict(X_train, verbose=0)
            p = target_distribution(q)
        loss = dec_model.train_on_batch(X_train, p)
        loss_history.append(loss)
    return loss_history

def evaluate_dec(encoder_model, dec_model, X_test, df_combined, idx_test):
    # Evaluate the DEC model using silhouette score and cluster accuracy
    X_latent_test = encoder_model.predict(X_test)
    q_final_test = dec_model.predict(X_test, verbose=0)
    pred_labels_dec_test = np.argmax(q_final_test, axis=1)
    df_combined_test = df_combined.loc[idx_test].copy()
    df_combined_test.reset_index(drop=True, inplace=True)
    df_combined_test['cluster'] = pred_labels_dec_test
    sil_score_dec_test = silhouette_score(X_latent_test, pred_labels_dec_test)
    
    def cluster_accuracy(true_labels, pred_labels):  
        cm = confusion_matrix(true_labels, pred_labels)
        row_ind, col_ind = linear_sum_assignment(-cm)
        return cm[row_ind, col_ind].sum() / np.sum(cm)
    
    true_labels_test = df_combined_test['true_label'].values
    clustering_accuracy = cluster_accuracy(true_labels_test, pred_labels_dec_test)
    
    return {
        "silhouette_score": sil_score_dec_test,
        "clustering_accuracy": clustering_accuracy,
        "predicted_clusters": pred_labels_dec_test.tolist(),
        "df_test": df_combined_test.to_dict(orient='records')
    }
