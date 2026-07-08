import cv2
import numpy as np
import torch
import torch.nn.functional as F
from typing import List, Optional
from insightface.app import FaceAnalysis
from ..config import settings

# Determine device and providers
is_gpu = torch.cuda.is_available()
device = torch.device("cuda:0" if is_gpu else "cpu")
providers = ["CUDAExecutionProvider"] if is_gpu else ["CPUExecutionProvider"]
ctx_id = 0 if is_gpu else -1

print(f"Imported utils module. Using device: {device}")

_det_rec_model = None
_det_model = None

def get_det_rec_model():
    global _det_rec_model
    if _det_rec_model is None:
        _det_rec_model = FaceAnalysis(name="buffalo_l", providers=providers, allowed_modules=["detection", "recognition"], root="/models")
        _det_rec_model.prepare(ctx_id=ctx_id, det_size=(320, 256), det_thresh=0.7)
    return _det_rec_model

def get_det_model():
    global _det_model
    if _det_model is None:
        _det_model = FaceAnalysis(name="buffalo_l", providers=providers, allowed_modules=["detection"], root="/models")
        _det_model.prepare(ctx_id=ctx_id, det_size=(320, 256), det_thresh=0.6)
    return _det_model


@torch.inference_mode()
def lighting_check_gpu(frames_tensor: torch.Tensor) -> torch.Tensor:
    """
    Computes lighting validity for a batch of frames directly on GPU.
    frames_tensor shape: (B, C, H, W)
    Returns a boolean mask of shape (B,) where True means lighting is OK.
    """
    tot_pixels = frames_tensor.shape[1] * frames_tensor.shape[2] * frames_tensor.shape[3]
    
    glare_pixels = torch.sum(frames_tensor >= 250, dim=(1, 2, 3))
    shadow_pixels = torch.sum(frames_tensor <= 10, dim=(1, 2, 3))
    
    glare_ratio = glare_pixels.float() / tot_pixels
    shadow_ratio = shadow_pixels.float() / tot_pixels
    
    return (glare_ratio <= 0.15) & (shadow_ratio <= 0.15)

@torch.inference_mode()
def compute_laplacian_batch_gpu(full_frame_bgr: torch.Tensor) -> torch.Tensor:
    
    gray_batch = 0.114*full_frame_bgr[:,0] + 0.587*full_frame_bgr[:,1] + 0.299*full_frame_bgr[:,2] 
    gray_batch = gray_batch.unsqueeze(1)
    padded_gray_batch = F.pad(gray_batch, (1, 1, 1, 1), mode='reflect')
    kernel = torch.tensor([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=torch.float32, device=full_frame_bgr.device).view(1, 1, 3, 3)
    
    full_laplacian = F.conv2d(padded_gray_batch, kernel).squeeze(1)
    return full_laplacian


def eval_faces_batch(faces_list: list, laplacian_batch: List[torch.tensor]) -> list[int]:
    """
    Evaluates a batch of faces parsed from sequential frames using vectorized GPU functions.
    """
    valid_face_counts = []
    for idx, faces in enumerate(faces_list):
        if len(faces) == 0:
            valid_face_counts.append(0)
            continue
            
        valid_indices = []
        full_laplacian = laplacian_batch[idx]
        img_h, img_w = full_laplacian.shape
        
        bboxes = np.array([face.bbox for face in faces], dtype=int)
        x1_all = np.clip(bboxes[:, 0] + 1, 0, img_w)
        y1_all = np.clip(bboxes[:, 1] + 1, 0, img_h)
        x2_all = np.clip(bboxes[:, 2] - 1, 0, img_w)
        y2_all = np.clip(bboxes[:, 3] - 1, 0, img_h)
        width = x2_all - x1_all
        height = y2_all - y1_all
        face_size_mask = (width * height) > settings.face_size_threshold
        variances = [torch.var(full_laplacian[y1:y2, x1:x2], unbiased=False).item() for x1, y1, x2, y2 in zip(x1_all, y1_all, x2_all, y2_all)]
        variance_mask = np.array(variances) >= settings.sharpness_threshold
        valid_mask = face_size_mask & variance_mask
        
                
        valid_indices = np.where(valid_mask)[0].tolist()    
        if not valid_indices:
            valid_face_counts.append(0)
            continue
        
        # Phase 3: Evaluate Symmetry and validate count
        valid_faces_in_frame = 0
        all_kps = np.array([faces[x].kps for x in valid_indices])
        left_eye = all_kps[:,0,:]
        right_eye = all_kps[:,1,:]
        nose = all_kps[:,2,:]
        dist_left = np.linalg.norm(nose-left_eye, axis=1)
        dist_right = np.linalg.norm(nose - right_eye, axis=1)
        max_dist = np.maximum(dist_left, dist_right)
        pose_symmetry = np.minimum(dist_left, dist_right)/np.clip(max_dist, 1e-5, None)
        valid_faces_in_frame = int(np.sum(pose_symmetry>settings.pose_symmetry_threshold))
        
        valid_face_counts.append(valid_faces_in_frame)
        
    return valid_face_counts

def select_nbd_frame_batch(point_frame: int, vid_object: cv2.VideoCapture, tot_frames: int) -> tuple[Optional[np.ndarray], int]:
    """
    Optimized Batch Extractor: Aggregates a neighborhood profile on GPU to avoid heavy 
    serial loop latencies.
    """
    det_model = get_det_model()
    start_frame = max(1, point_frame - settings.num_eval_nbd_frames)
    end_frame = min(tot_frames, point_frame + settings.num_eval_nbd_frames)
    frames_np = []
    vid_object.set(cv2.CAP_PROP_POS_FRAMES, start_frame - 1)
    for i in range(start_frame, end_frame + 1, 2):
        ret, img = vid_object.read()
        if ret:
            img_resized = cv2.resize(img, (320, 256))
            frames_np.append(img_resized)
        vid_object.grab()            
    if not frames_np:
        return None, 0
    
    '''
    # PERFORMANCE BOOST: Use pin_memory before shipping to GPU to enable non-blocking DMA speeds
    stacked_np = np.stack(frames_np)
    cpu_tensor = torch.from_numpy(stacked_np).pin_memory()
    frames_tensor = cpu_tensor.to(device, non_blocking=True).float() # Cast to float immediately
    '''

    frames_tensor = torch.from_numpy(np.stack(frames_np)).to(device).float() # Shape: (B, H, W, C)
    frames_tensor = frames_tensor.permute(0, 3, 1, 2)  # Change to (B, C, H, W) for convolution operations
    lighting_mask = lighting_check_gpu(frames_tensor)
    
    min_good_frames = len(frames_np) // 2
    if torch.sum(lighting_mask).item() < min_good_frames:
        print(f"No lighting in frame:{point_frame}")
        return None, 0
    
    laplacian_batch = compute_laplacian_batch_gpu(frames_tensor)
    
    laplacian_batch_list = []
    valid_frames = []
    for idx, is_valid in enumerate(lighting_mask):  # We will have at most 8-10 frames, so this loop will run that times only.
        if is_valid.item():
            valid_frames.append(frames_np[idx])
            laplacian_batch_list.append(laplacian_batch[idx])
           
    if not valid_frames:
        return None, 0

    faces_list = [det_model.get(f) for f in valid_frames]
    
    tot_face_per_frame = eval_faces_batch(faces_list, laplacian_batch_list)
    best_frame_idx = np.argmax(tot_face_per_frame)
    if tot_face_per_frame[best_frame_idx] == 0:
        return None, 0
    return valid_frames[best_frame_idx], int(tot_face_per_frame[best_frame_idx])