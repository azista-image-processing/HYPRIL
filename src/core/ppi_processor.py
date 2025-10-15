import time
# ppi_processor.py
import cupy as cp
import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import plotly.graph_objects as go
import plotly.express as px
from typing import List, Dict, Optional, Tuple
import numpy as np


class PPI_Processor:
    """
    Complete ENVI-like backend for hyperspectral endmember extraction and abundance mapping.
    """
    def __init__(self):
        self.all_layers: List[Dict] = []

        # self.selected_layer: Optional[Dict] = None
        self.processing_layer: Optional[Dict] = None
        self.original_layer: Optional[Dict] = None

        self.endmembers: Optional[np.ndarray] = None
        self.endmember_indices: Optional[np.ndarray] = None
        self.endmember_clusters: Optional[List[Dict]] = None
        self.ppi_scores: Optional[np.ndarray] = None
        self.abundance_maps: Optional[np.ndarray] = None

    def add_layer(self, layer: dict):
        """Adds a layer to the available layers for processing."""
        self.all_layers.append(layer)
        print(f"Added layer '{layer['name']}' with shape {layer['data'].shape}")

    def set_input_layers(self, processing_layer_index: int, original_layer_index: int):
        """Sets both the processing (MNF) and original (full-band) layers."""
        if not (0 <= processing_layer_index < len(self.all_layers) and \
                0 <= original_layer_index < len(self.all_layers)):
            raise IndexError("Layer index is out of bounds.")
            
        self.processing_layer = self.all_layers[processing_layer_index]
        self.original_layer = self.all_layers[original_layer_index]
        
        # Reset previous results
        self.endmembers = None
        self.ppi_scores = None
        self.abundance_maps = None
        print(f"Processing Layer set to: {self.processing_layer['name']}")
        print(f"Original Layer set to: {self.original_layer['name']}")


    def calculate_ppi(self, num_iterations: int = 10000, threshold_factor: float = 0.10) -> np.ndarray:
        """Calculate PPI scores with threshold-based extrema detection."""
        start_time = cp.cuda.Event()
        start_time.record()
        # threshold = self.ppi_threshold_spin.value()
        print(f"using thresshold of {threshold_factor}")

        
        if self.processing_layer is None:
            raise ValueError("Processing (MNF) layer not set.")
        
        self.data = self.processing_layer['data']
        original_shape = self.data.shape
        
        print(f"Original Data Shape: {original_shape}")
        data_2d = self.data.reshape(-1, original_shape[-1])
        use_gpu = False
        if use_gpu == True:
            start_time= cp.cuda.Event()
            start_time.record()
            print("Using GPU to calculate PPI.....................")
            data_2d_xp = cp.asanyarray(data_2d)
            # Normalize data (handle zero vectors)
            # norms = np.linalg.norm(data_2d, axis=1, keepdims=True)
            norms = cp.linalg.norm(data_2d_xp ,axis =1, keepdims=True)
            norms[norms == 0] = 1
            # data_2d_normalized = data_2d / norms
            data_2d_normalized = data_2d_xp / norms
            
            # num_pixels, num_bands = data_2d.shape
            num_pixels, num_bands = data_2d_xp.shape
            # ppi_scores = np.zeros(num_pixels, dtype=np.float32)
            ppi_scores = cp.zeros(num_pixels, dtype=cp.float32)
            
            print(f"Calculating PPI with {num_iterations} iterations (threshold: {threshold_factor})...")
            
            # Generate all skewers at once for efficiency
            # skewers = np.random.randn(num_iterations, num_bands)
            # skewers /= np.linalg.norm(skewers, axis=1, keepdims=True)
            skewers = cp.random.randn(num_iterations, num_bands)
            skewers /= cp.linalg.norm(skewers, axis=1, keepdims=True)
            
            batch_size = 1000  # Process 1000 skewers at a time to manage memory usage  
            num_batches = (num_iterations + batch_size - 1) // batch_size



            for batch_start in range(0, num_iterations, batch_size):
                batch_end = min(batch_start + batch_size, num_iterations)
                batch_size_actual = batch_end - batch_start
                
                # Subset of skewers for this batch
                batch_skewers = skewers[batch_start:batch_end]
                
                # Project batch (small enough to fit in memory)
                batch_projections = data_2d_normalized @ batch_skewers.T  # Shape: (num_pixels, batch_size_actual)
                
                # Vectorized extrema detection for batch
                max_vals = cp.max(batch_projections, axis=0)
                min_vals = cp.min(batch_projections, axis=0)
                projection_ranges = max_vals - min_vals
                # print("projection_ranges",projection_ranges)
                thresholds = projection_ranges * threshold_factor
                
                # Masks (broadcasting over pixels and batch skewers)
                max_extremes_mask = batch_projections >= (max_vals[None, :] - thresholds[None, :])
                min_extremes_mask = batch_projections <= (min_vals[None, :] + thresholds[None, :])
                
                # Sum masks along batch axis and add to total PPI
                ppi_scores += cp.sum(max_extremes_mask, axis=1, dtype=cp.float32)
                ppi_scores += cp.sum(min_extremes_mask, axis=1, dtype=cp.float32)
                
                # Explicitly delete batch to free memory
                # del batch_projections, max_vals, min_vals, projection_ranges, thresholds
                
                del max_vals, min_vals, projection_ranges, thresholds
                max_extremes_mask = None  # CuPy GC hint
                min_extremes_mask = None
                
                # Progress
                progress = (batch_end / num_iterations) * 100
                print(f"  Progress: {batch_end}/{num_iterations} iterations ({progress:.1f}%)")
            # Transfer back to CPU only at the end


            ppi_scores_cpu = ppi_scores.get() if use_gpu else ppi_scores
            print(f"ppi_scores shape after get: {ppi_scores_cpu.shape}")
            self.ppi_score = ppi_scores_cpu.reshape(original_shape[0], original_shape[1])
                # Skewers are small; transfer back
            self.skewers = skewers.get() if use_gpu else skewers
            self.batch_projections = batch_projections.get() if use_gpu else batch_projections
            end_time = cp.cuda.Event()
            end_time.record()

            end_time.synchronize()

            # Calculate elapsed time in milliseconds
            elapsed_time_ms = cp.cuda.get_elapsed_time(start_time, end_time)
            elapsed_time_sec = elapsed_time_ms / 1000
            print(f"Time Taken {elapsed_time_sec} seconds")
            print(f"PPI calculation completed with thresshold {threshold_factor} in {num_iterations} in time {elapsed_time_sec} .")
            #saving the ppi score as numpy array
            # np.save("ppi_score.npy", self.ppi_score)

            end_time = cp.cuda.Event()
            end_time.record()
            end_time.synchronize()
            # Calculate elapsed time in milliseconds
            elapsed_time_ms = cp.cuda.get_elapsed_time(start_time, end_time)
            elapsed_time_sec = elapsed_time_ms / 1000
            print(f"Time Taken with GPU {elapsed_time_sec} seconds")
            return self.ppi_score, self.batch_projections , self.skewers
        
        else:
            start_time = time.time()
            print("Using CPU to calculate PPI..........")
            # Normalize data (handle zero vectors)
            norms = np.linalg.norm(data_2d, axis=1, keepdims=True)
            norms[norms == 0] = 1
            data_2d_normalized = data_2d / norms            
            num_pixels, num_bands = data_2d.shape
            ppi_scores = np.zeros(num_pixels, dtype=np.float32)            
            print(f"Calculating PPI with {num_iterations} iterations (threshold: {threshold_factor})...")
            # Generate all skewers at once for efficiency
            skewers = np.random.randn(num_iterations, num_bands)
            skewers /= np.linalg.norm(skewers, axis=1, keepdims=True)
            # Project all data onto all skewers
            projections = data_2d_normalized @ skewers.T  # Shape: (num_pixels, num_iterations)
            # print("Projection shape",projections.shape)
            
            # Find extrema for each skewer with threshold
            for j in range(num_iterations):
                projection = projections[:, j]
                max_val = np.max(projection)
                min_val = np.min(projection)
                projection_range = max_val - min_val
                # print(f"projetion range for iteration {j}: {projection_range}")

                threshold = projection_range*threshold_factor
                # print(f"Threshold: {threshold}")
                
                # Find pixels within threshold of extrema
                max_extremes = np.where(projection >= (max_val - threshold))[0]
                min_extremes = np.where(projection <= (min_val + threshold))[0]
                
                # Increment PPI scores
                ppi_scores[max_extremes] += 1
                ppi_scores[min_extremes] += 1
                
                # Progress reporting
                if (j + 1) % 500 == 0:
                    print(f"  Progress: {j+1}/{num_iterations} iterations")
            
            self.ppi_scores = ppi_scores.reshape(original_shape[0], original_shape[1])
            print(f"Total extreme count : {np.count_nonzero(ppi_scores)}  ")
            self.projections = projections
            self.skewers = skewers
            print(f"PPI calculation completed with thresshold {threshold_factor} in {num_iterations}.")
            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f"Time Taken with CPU {elapsed_time} seconds")
            # self.plot_ppi_3d(self.data, self.ppi_scores)
            return self.ppi_scores, self.projections , self.skewers



    def extract_endmembers(self, num_endmembers: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """Extract endmembers using clustering on high-PPI pixels."""
        if self.ppi_score is None:
            raise ValueError("PPI scores not calculated.")

        original_data  = self.original_layer['data']
        data_2d = original_data.reshape(-1, original_data.shape[-1])
        ppi_1d = self.ppi_score.flatten()

        self.all_pixel = ppi_1d

        top_percentile = 98
        threshold = np.percentile(ppi_1d[ppi_1d > 0], top_percentile)
        pure_pixel_mask = ppi_1d >= threshold
        
        if not np.any(pure_pixel_mask):
             raise ValueError(f"No pixels found above {top_percentile}th percentile. Try a lower PPI score threshold or more iterations.")

        pure_pixels = data_2d[pure_pixel_mask]
        pure_indices = np.where(pure_pixel_mask)[0]

        kmeans = KMeans(n_clusters=num_endmembers, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(pure_pixels)
        
        endmember_clusters = []
        for i in range(num_endmembers):
            cluster_mask = cluster_labels == i
            if np.any(cluster_mask):
                cluster_pixels_data = pure_pixels[cluster_mask]
                cluster_pixel_indices = pure_indices[cluster_mask]
                cluster_ppi_scores = ppi_1d[cluster_pixel_indices]

                best_idx_in_cluster = np.argmax(cluster_ppi_scores)
                endmember_clusters.append({
                    'spectrum': cluster_pixels_data[best_idx_in_cluster],
                    'index': cluster_pixel_indices[best_idx_in_cluster],
                    'cluster_pixels': cluster_pixels_data,
                })
        
        self.endmembers = np.array([c['spectrum'] for c in endmember_clusters])
        self.endmember_indices = np.array([c['index'] for c in endmember_clusters])
        self.endmember_clusters = endmember_clusters

        print(f"Extracted {len(self.endmembers)} endmembers.")
        return self.endmembers, self.endmember_indices, self.all_pixel

    def visualize_ndimensional(self, num_components: int = 3) -> go.Figure:
        """Create n-dimensional visualization using Plotly."""
        if self.endmember_clusters is None:
            raise ValueError("Endmembers not extracted.")

        all_cluster_pixels = np.vstack([c['cluster_pixels'] for c in self.endmember_clusters])

        pca = PCA(n_components=num_components)
        reduced_data = pca.fit_transform(all_cluster_pixels)
        
        fig = go.Figure()
        colors = px.colors.qualitative.Plotly
        
        start_idx = 0
        for i, cluster in enumerate(self.endmember_clusters):
            num_points = len(cluster['cluster_pixels'])
            end_idx = start_idx + num_points
            
            cluster_reduced = reduced_data[start_idx:end_idx]
            endmember_reduced = pca.transform(cluster['spectrum'].reshape(1, -1))[0]
            
            # Plot cluster points
            fig.add_trace(go.Scatter3d(
                x=cluster_reduced[:, 0], y=cluster_reduced[:, 1], z=cluster_reduced[:, 2],
                mode='markers',
                marker=dict(size=2, color=colors[i % len(colors)], opacity=0.6),
                name=f'Cluster {i+1}'
            ))
            
            # Highlight endmember point
            fig.add_trace(go.Scatter3d(
                x=[endmember_reduced[0]], y=[endmember_reduced[1]], z=[endmember_reduced[2]],
                mode='markers',
                marker=dict(size=8, color=colors[i % len(colors)], symbol='diamond',
                            line=dict(color='Black', width=2)),
                name=f'Endmember {i+1}'
            ))
            start_idx = end_idx
            
        fig.update_layout(
            title="n-Dimensional Endmember Visualizer",
            scene=dict(xaxis_title="PC 1", yaxis_title="PC 2", zaxis_title="PC 3"),
            margin=dict(l=0, r=0, b=0, t=40),
            height=700
        )
        return fig
    


    def calculate_abundance_maps(self, add_shade_endmember: bool = True) -> np.ndarray:
        """Calculate abundance maps using FCLS (via pseudo-inverse with constraints)."""
        if self.endmembers is None or self.original_layer is None:
            raise ValueError("Endmembers not extracted.")

        data = self.original_layer['data']
        h, w, bands = data.shape
        data_2d = data.reshape(-1, bands)
        

        endmembers_matrix = self.endmembers.T  # Shape: (bands, num_endmembers)
        
        if add_shade_endmember:
            shade = np.zeros((bands, 1))  # Shape: (bands, 1)
            endmembers_matrix = np.hstack([endmembers_matrix, shade])
        
        num_em = endmembers_matrix.shape[1]
        
        print(f"Data shape: {data_2d.shape}")
        print(f"Endmembers matrix shape: {endmembers_matrix.shape}")
        print(f"Number of endmembers (including shade): {num_em}")

        try:
            # Calculate pseudo-inverse of endmembers matrix
            pinv_em = np.linalg.pinv(endmembers_matrix)  # Shape: (num_em, bands)
            print(f"Pseudo-inverse shape: {pinv_em.shape}")
            
            # Solve for abundances: (num_em, bands) @ (bands, num_pixels) = (num_em, num_pixels)
            abundances = pinv_em @ data_2d.T  # Shape: (num_em, num_pixels)
            abundances = abundances.T  # Transpose to (num_pixels, num_em)
            
        except np.linalg.LinAlgError:
            print("Pseudo-inverse failed, using least squares approach...")
            # Alternative approach using lstsq
            abundances = np.zeros((data_2d.shape[0], num_em))
            for i, pixel in enumerate(data_2d):
                ab, _, _, _ = np.linalg.lstsq(endmembers_matrix, pixel, rcond=None)
                abundances[i] = ab
        
        # Apply constraints: non-negativity and sum-to-one
        abundances[abundances < 0] = 0
        row_sums = abundances.sum(axis=1)
        row_sums[row_sums == 0] = 1  # Avoid division by zero
        abundances = abundances / row_sums[:, np.newaxis]

        self.abundance_maps = abundances.reshape(h, w, num_em)
        print(f"Abundance maps shape: {self.abundance_maps.shape}")
        print("Abundance mapping completed.")
        return self.abundance_maps